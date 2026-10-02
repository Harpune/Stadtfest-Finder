"""REST adapter tests for `/v1/mod/ai-searches` (fakes): 202, 409, 422, 429, 404."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from stadtfest.adapters.inbound.rest import mod_ai_searches
from stadtfest.adapters.inbound.rest.auth import optional_principal
from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.application.ai_ingestion.use_cases import (
    AiSearchSettings,
    GetAiSearch,
    ListAiSearches,
    StartAiSearch,
)
from stadtfest.application.geocoding.ports import Place, PlaceKind
from stadtfest.application.identity.claims import ClaimMapping
from stadtfest.application.identity.use_cases import Authenticate
from stadtfest.application.moderation.ports import ModRegion
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.events.region import Region
from tests.fakes import (
    FakeAccountResolver,
    FakeAiSearchRepository,
    FakeDeletedAccounts,
    FakeGeocoding,
    FakeModRegions,
    FakeTokenVerifier,
    FixedClock,
)

OSTALB = ModRegion(uuid4(), Region("ostalb", "Ostalb", frozenset({"73430"})))
MOD = {"Authorization": "Bearer mod"}
OTHER = {"Authorization": "Bearer other"}
USER = {"Authorization": "Bearer user"}


@pytest.fixture
def client() -> TestClient:
    verifier = FakeTokenVerifier(
        {
            "mod": {"sub": "m", "realm_access": {"roles": ["moderator"]}, "region": "ostalb"},
            "other": {"sub": "o", "realm_access": {"roles": ["moderator"]}, "region": "ostalb"},
            "user": {"sub": "u", "realm_access": {"roles": ["user"]}},
        }
    )
    jobs = FakeAiSearchRepository()
    regions = FakeModRegions({"ostalb": OSTALB})
    accounts = FakeAccountResolver()
    geocoding = FakeGeocoding(
        places=[Place("73430 Aalen", "Aalen", GeoPoint(48.8, 10.1), PlaceKind.POSTCODE, "73430")]
    )
    app = FastAPI(dependencies=[Depends(optional_principal)])
    register_error_handlers(app)
    app.include_router(mod_ai_searches.router)
    app.state.container = SimpleNamespace(
        authenticate=Authenticate(
            verifier, ClaimMapping("realm_access.roles", "region"), FakeDeletedAccounts()
        ),
        start_ai_search=StartAiSearch(
            jobs,
            regions,
            accounts,
            geocoding,
            FixedClock(date(2026, 10, 2)),
            AiSearchSettings(daily_limit=2),
            now=lambda: datetime(2026, 10, 2, 9, tzinfo=UTC),
        ),
        get_ai_search=GetAiSearch(jobs, regions, accounts),
        list_ai_searches=ListAiSearches(jobs, regions, accounts),
    )
    return TestClient(app)


def test_start_returns_202_and_the_job(client: TestClient) -> None:
    response = client.post("/v1/mod/ai-searches", json={"postalCode": "73430"}, headers=MOD)

    assert response.status_code == 202
    body = response.json()
    assert (body["status"], body["placeName"], body["newEventIds"]) == ("queued", "Aalen", [])
    assert body["skipped"] == {
        "duplicate": 0,
        "outOfRegion": 0,
        "invalid": 0,
        "unverifiedSource": 0,
    }
    job = client.get(f"/v1/mod/ai-searches/{body['id']}", headers=MOD)
    assert job.json()["id"] == body["id"]
    running = client.get("/v1/mod/ai-searches", params={"status": "running"}, headers=MOD)
    assert [j["id"] for j in running.json()] == [body["id"]]
    assert client.get(f"/v1/mod/ai-searches/{body['id']}", headers=OTHER).status_code == 404


def test_second_start_conflicts_with_the_running_job(client: TestClient) -> None:
    first = client.post("/v1/mod/ai-searches", json={"postalCode": "73430"}, headers=MOD).json()

    second = client.post("/v1/mod/ai-searches", json={"postalCode": "73430"}, headers=MOD)

    assert second.status_code == 409
    assert second.json()["error"] == "search_running"
    assert second.json()["fields"] == {"jobId": first["id"]}


def test_outside_region_invalid_code_and_roles(client: TestClient) -> None:
    outside = client.post("/v1/mod/ai-searches", json={"postalCode": "89073"}, headers=MOD)
    assert (outside.status_code, outside.json()["error"]) == (422, "postal_code_outside_region")
    assert (
        client.post("/v1/mod/ai-searches", json={"postalCode": "734"}, headers=MOD).status_code
        == 422
    )
    assert (
        client.post("/v1/mod/ai-searches", json={"postalCode": "73430"}, headers=USER).status_code
        == 403
    )
