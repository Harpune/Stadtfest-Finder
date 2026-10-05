"""REST adapter tests for `/v1/mod/events` (fake repository, no database)."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from stadtfest.adapters.inbound.rest import mod_events
from stadtfest.adapters.inbound.rest.auth import optional_principal
from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.identity.claims import ClaimMapping
from stadtfest.application.identity.use_cases import Authenticate
from stadtfest.application.moderation.use_cases import (
    CancelModEvent,
    CreateModEvent,
    DeleteModEvent,
    GetModEvent,
    ListModEvents,
    PublishModEvent,
    UnpublishModEvent,
    UpdateModEvent,
)
from tests.fakes import (
    FakeAccountResolver,
    FakeActiveCategories,
    FakeDeletedAccounts,
    FakeManagedEventRepository,
    FakeTokenVerifier,
    FixedClock,
)

CATEGORY = uuid4()
MOD = {"Authorization": "Bearer mod"}
USER = {"Authorization": "Bearer user"}


@pytest.fixture
def client() -> TestClient:
    verifier = FakeTokenVerifier(
        {
            "mod": {"sub": "m", "realm_access": {"roles": ["moderator"]}},
            "user": {"sub": "u", "realm_access": {"roles": ["user"]}},
        }
    )
    base = (
        FakeManagedEventRepository(),
        FixedClock(date(2026, 10, 1)),
    )
    accounts = FakeAccountResolver()
    app = FastAPI(dependencies=[Depends(optional_principal)])
    register_error_handlers(app)
    app.include_router(mod_events.router)
    app.state.container = SimpleNamespace(
        authenticate=Authenticate(
            verifier, ClaimMapping("realm_access.roles"), FakeDeletedAccounts()
        ),
        image_urls=ImageUrls("https://img.test/bucket"),
        list_mod_events=ListModEvents(*base),
        get_mod_event=GetModEvent(*base),
        create_mod_event=CreateModEvent(*base, accounts),
        update_mod_event=UpdateModEvent(*base, accounts),
        publish_mod_event=PublishModEvent(
            *base,
            accounts,
            FakeActiveCategories(frozenset({CATEGORY})),
            now=lambda: datetime(2026, 10, 1, tzinfo=UTC),
        ),
        unpublish_mod_event=UnpublishModEvent(*base, accounts),
        cancel_mod_event=CancelModEvent(*base, accounts),
        delete_mod_event=DeleteModEvent(*base, accounts),
    )
    return TestClient(app)


def _create(client: TestClient) -> str:
    response = client.post("/v1/mod/events", json={"name": "Herbstfest"}, headers=MOD)
    assert response.status_code == 201
    assert response.headers["ETag"] == '"1"'
    body = response.json()
    assert (body["status"], body["shortName"], body["version"]) == ("draft", "Herbstfest", 1)
    return str(body["id"])


def _patch(client: TestClient, event_id: str, body: dict[str, object], version: str) -> Response:
    response: Response = client.patch(
        f"/v1/mod/events/{event_id}",
        json=body,
        headers=MOD | {"If-Match": version, "Content-Type": "application/merge-patch+json"},
    )
    return response


def test_users_without_the_role_are_forbidden(client: TestClient) -> None:
    response = client.get("/v1/mod/events", headers=USER)
    assert response.status_code == 403
    assert client.get("/v1/mod/events").status_code == 401


def test_full_lifecycle(client: TestClient) -> None:
    event_id = _create(client)

    incomplete = client.post(f"/v1/mod/events/{event_id}/publish", headers=MOD)
    assert incomplete.status_code == 422
    assert incomplete.json()["fields"]["startDate"] == "required"

    patched = _patch(
        client,
        event_id,
        {
            "categoryId": str(CATEGORY),
            "startDate": "2026-10-17",
            "endDate": "2026-10-18",
            "place": "Festplatz",
            "city": "Aalen",
            "postalCode": "73430",
            "lat": 48.86,
            "lon": 10.1,
            "openingHours": ["Sa 11-24 Uhr", "  "],
            "program": [{"date": "2026-10-17", "timeLabel": "11 Uhr", "title": "Fassanstich"}],
        },
        '"1"',
    )
    assert patched.status_code == 200
    assert patched.headers["ETag"] == '"2"'
    assert patched.json()["openingHours"] == ["Sa 11-24 Uhr"]

    published = client.post(f"/v1/mod/events/{event_id}/publish", headers=MOD)
    assert published.json()["status"] == "published"
    cancelled = client.post(
        f"/v1/mod/events/{event_id}/cancel", json={"reason": "Sturm"}, headers=MOD
    )
    assert cancelled.json()["cancelReason"] == "Sturm"

    listed = client.get("/v1/mod/events", params={"status": "cancelled"}, headers=MOD).json()
    assert [item["id"] for item in listed["items"]] == [event_id]

    assert client.delete(f"/v1/mod/events/{event_id}", headers=MOD).status_code == 204
    assert client.get(f"/v1/mod/events/{event_id}", headers=MOD).status_code == 404


def test_status_filter_is_applied(client: TestClient) -> None:
    """The filter was silently ignored (generated RootModel as query type, 05.10.2026)."""
    _create(client)

    drafts = client.get("/v1/mod/events", params={"status": "draft"}, headers=MOD).json()
    cancelled = client.get("/v1/mod/events", params={"status": "cancelled"}, headers=MOD).json()

    assert len(drafts["items"]) == 1
    assert cancelled["items"] == []
    assert client.get("/v1/mod/events", params={"status": "x"}, headers=MOD).status_code == 422


def test_patch_needs_if_match(client: TestClient) -> None:
    event_id = _create(client)
    response = client.patch(
        f"/v1/mod/events/{event_id}",
        json={"price": "Frei"},
        headers=MOD | {"Content-Type": "application/merge-patch+json"},
    )
    assert response.status_code == 428
    assert response.json()["error"] == "precondition_required"


def test_stale_version_conflicts(client: TestClient) -> None:
    event_id = _create(client)
    assert _patch(client, event_id, {"price": "Frei"}, "1").status_code == 200
    stale = _patch(client, event_id, {"price": "5 €"}, 'W/"1"')
    assert stale.status_code == 409
    assert stale.json()["error"] == "version_conflict"


def test_invalid_transition_and_publish_anywhere(client: TestClient) -> None:
    event_id = _create(client)
    cancel = client.post(f"/v1/mod/events/{event_id}/cancel", headers=MOD)
    assert cancel.status_code == 409
    assert cancel.json()["error"] == "invalid_transition"

    _patch(
        client,
        event_id,
        {
            "categoryId": str(CATEGORY),
            "startDate": "2026-10-17",
            "endDate": "2026-10-18",
            "postalCode": "89073",
            "lat": 48.4,
            "lon": 9.99,
        },
        "1",
    )
    # Ulm, far from the old moderator region: no regions anymore (ADR 0015).
    published = client.post(f"/v1/mod/events/{event_id}/publish", headers=MOD)
    assert published.status_code == 200
    assert "regionId" not in published.json()
