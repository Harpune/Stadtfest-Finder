"""REST adapter tests for `/v1/me/favorites` and `isFavorite` on the event detail."""

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from stadtfest.adapters.inbound.rest import events, favorites
from stadtfest.adapters.inbound.rest.auth import optional_principal
from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.application.collections.use_cases import (
    AddFavorite,
    IsFavorite,
    ListFavorites,
    RemoveFavorite,
)
from stadtfest.application.events.use_cases import GetPublicEvent
from stadtfest.application.identity.claims import ClaimMapping
from stadtfest.application.identity.use_cases import Authenticate
from tests.fakes import (
    FakeAccountResolver,
    FakeDeletedAccounts,
    FakeEventCatalog,
    FakeFavoriteRepository,
    FakeTokenVerifier,
    FixedClock,
)
from tests.unit.rest.test_catalog_api import TODAY, _detail, _summary

TOKEN = "lena-token"
PAST = replace(
    _summary("Ipfmesse"),
    start_date=TODAY - timedelta(days=90),
    end_date=TODAY - timedelta(days=85),
)
RUNNING = _summary("Reichsstädter Tage")


@pytest.fixture
def repository() -> FakeFavoriteRepository:
    return FakeFavoriteRepository(public={PAST.id: PAST, RUNNING.id: RUNNING})


@pytest.fixture
def client(repository: FakeFavoriteRepository) -> TestClient:
    verifier = FakeTokenVerifier({TOKEN: {"sub": "sub-lena", "realm_access": {"roles": []}}})
    catalog = FakeEventCatalog(details={RUNNING.id: _detail(RUNNING.id)})
    app = FastAPI(dependencies=[Depends(optional_principal)])
    register_error_handlers(app)
    app.include_router(events.router)
    app.include_router(favorites.router)
    app.state.container = SimpleNamespace(
        authenticate=Authenticate(
            verifier, ClaimMapping("realm_access.roles", "region"), FakeDeletedAccounts()
        ),
        get_public_event=GetPublicEvent(catalog),
        add_favorite=AddFavorite(repository, FakeAccountResolver()),
        remove_favorite=RemoveFavorite(repository),
        list_favorites=ListFavorites(repository, FixedClock(TODAY)),
        is_favorite=IsFavorite(repository),
    )
    return TestClient(app)


AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/v1/me/favorites"), ("PUT", f"/v1/me/favorites/{uuid4()}")],
)
def test_favorites_require_a_token(client: TestClient, method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401


def test_put_and_delete_are_idempotent(
    client: TestClient, repository: FakeFavoriteRepository
) -> None:
    path = f"/v1/me/favorites/{RUNNING.id}"
    assert client.put(path, headers=AUTH).status_code == 204
    assert client.put(path, headers=AUTH).status_code == 204
    assert repository.counts[RUNNING.id] == 1

    assert client.delete(path, headers=AUTH).status_code == 204
    assert client.delete(path, headers=AUTH).status_code == 204
    assert repository.counts[RUNNING.id] == 0


def test_put_unknown_or_draft_event_is_not_found(client: TestClient) -> None:
    response = client.put(f"/v1/me/favorites/{uuid4()}", headers=AUTH)
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_list_returns_entries_and_past_only_on_request(client: TestClient) -> None:
    for event in (RUNNING, PAST):
        client.put(f"/v1/me/favorites/{event.id}", headers=AUTH)

    upcoming = client.get("/v1/me/favorites", headers=AUTH).json()["items"]
    everything = client.get("/v1/me/favorites", params={"include": "past"}, headers=AUTH)

    assert [item["name"] for item in upcoming] == ["Reichsstädter Tage"]
    assert upcoming[0]["categoryName"] == "Stadtfest"
    assert upcoming[0]["emoji"] == "🎪"
    assert "favoritedAt" in upcoming[0]
    assert [item["name"] for item in everything.json()["items"]] == [
        "Ipfmesse",
        "Reichsstädter Tage",
    ]


def test_list_rejects_unknown_include(client: TestClient) -> None:
    response = client.get("/v1/me/favorites", params={"include": "all"}, headers=AUTH)
    assert response.status_code == 422


def test_detail_contains_is_favorite_only_with_a_token(client: TestClient) -> None:
    path = f"/v1/events/{RUNNING.id}"
    assert "isFavorite" not in client.get(path).json()
    assert client.get(path, headers=AUTH).json()["isFavorite"] is False

    client.put(f"/v1/me/favorites/{RUNNING.id}", headers=AUTH)

    assert client.get(path, headers=AUTH).json()["isFavorite"] is True
