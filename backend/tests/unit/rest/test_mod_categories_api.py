"""REST adapter tests for `/v1/mod/categories` (fake repository): roles, validation, delete."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from stadtfest.adapters.inbound.rest import mod_categories
from stadtfest.adapters.inbound.rest.auth import optional_principal
from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.application.identity.claims import ClaimMapping
from stadtfest.application.identity.use_cases import Authenticate
from stadtfest.application.moderation.categories import (
    CreateCategory,
    DeleteCategory,
    ListModCategories,
    ModCategoryView,
    OrderCategories,
    UpdateCategory,
)
from tests.fakes import FakeCategoryRepository, FakeDeletedAccounts, FakeTokenVerifier

ADMIN = {"Authorization": "Bearer admin"}
MOD = {"Authorization": "Bearer mod"}
USER = {"Authorization": "Bearer user"}
STADTFEST = ModCategoryView(uuid4(), "Stadtfest", "🎪", "#FFB547", True, 0, 0)
VOLKSFEST = ModCategoryView(uuid4(), "Volksfest & Kirmes", "🎡", "#FF6B8B", True, 1, 0)


@pytest.fixture
def client() -> TestClient:
    verifier = FakeTokenVerifier(
        {
            "admin": {
                "sub": "a",
                "realm_access": {"roles": ["moderator", "category_admin"]},
            },
            "mod": {"sub": "m", "realm_access": {"roles": ["moderator"]}},
            "user": {"sub": "u", "realm_access": {"roles": ["user"]}},
        }
    )
    repo = FakeCategoryRepository(categories=[STADTFEST, VOLKSFEST], events={VOLKSFEST.id: 3})
    app = FastAPI(dependencies=[Depends(optional_principal)])
    register_error_handlers(app)
    app.include_router(mod_categories.router)
    app.state.container = SimpleNamespace(
        authenticate=Authenticate(
            verifier, ClaimMapping("realm_access.roles"), FakeDeletedAccounts()
        ),
        list_mod_categories=ListModCategories(repo),
        create_category=CreateCategory(repo),
        update_category=UpdateCategory(repo),
        order_categories=OrderCategories(repo),
        delete_category=DeleteCategory(repo),
    )
    return TestClient(app)


NEW = {"name": "Weinfest", "emoji": "🍷", "color": "#C792EA"}


def test_moderators_read_and_users_are_forbidden(client: TestClient) -> None:
    listed = client.get("/v1/mod/categories", headers=MOD)
    assert listed.status_code == 200
    assert listed.json()[1] == {
        "id": str(VOLKSFEST.id),
        "name": "Volksfest & Kirmes",
        "emoji": "🎡",
        "color": "#FF6B8B",
        "active": True,
        "sortOrder": 1,
        "eventCount": 3,
    }
    assert client.get("/v1/mod/categories", headers=USER).status_code == 403
    assert client.get("/v1/mod/categories").status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/v1/mod/categories", NEW),
        ("PATCH", f"/v1/mod/categories/{STADTFEST.id}", {"active": False}),
        ("PUT", "/v1/mod/categories/order", {"ids": [str(VOLKSFEST.id), str(STADTFEST.id)]}),
        ("DELETE", f"/v1/mod/categories/{STADTFEST.id}", None),
    ],
)
def test_writing_without_category_admin_is_forbidden(
    client: TestClient, method: str, path: str, body: object
) -> None:
    response = client.request(method, path, json=body, headers=MOD)
    assert response.status_code == 403


def test_admin_creates_updates_and_orders(client: TestClient) -> None:
    created = client.post("/v1/mod/categories", json=NEW, headers=ADMIN)
    assert created.status_code == 201
    assert (created.json()["sortOrder"], created.json()["active"]) == (2, True)

    duplicate = client.post("/v1/mod/categories", json=NEW | {"name": "WEINFEST"}, headers=ADMIN)
    assert duplicate.status_code == 422
    assert duplicate.json()["fields"] == {"name": "duplicate"}

    patched = client.patch(
        f"/v1/mod/categories/{STADTFEST.id}", json={"active": False}, headers=ADMIN
    )
    assert patched.json()["active"] is False

    ordered = client.put(
        "/v1/mod/categories/order",
        json={"ids": [created.json()["id"], str(VOLKSFEST.id), str(STADTFEST.id)]},
        headers=ADMIN,
    )
    assert [c["name"] for c in ordered.json()] == ["Weinfest", "Volksfest & Kirmes", "Stadtfest"]


def test_emoji_and_color_must_be_presets(client: TestClient) -> None:
    response = client.post(
        "/v1/mod/categories", json=NEW | {"emoji": "🦄", "color": "#123456"}, headers=ADMIN
    )
    assert response.status_code == 422


def test_delete_with_events_needs_a_replacement(client: TestClient) -> None:
    missing = client.delete(f"/v1/mod/categories/{VOLKSFEST.id}", headers=ADMIN)
    assert missing.status_code == 422
    assert missing.json()["error"] == "replacement_required"

    moved = client.delete(
        f"/v1/mod/categories/{VOLKSFEST.id}",
        params={"replacementId": str(STADTFEST.id)},
        headers=ADMIN,
    )
    assert moved.status_code == 200
    assert moved.json() == {"movedEvents": 3, "replacementId": str(STADTFEST.id)}
