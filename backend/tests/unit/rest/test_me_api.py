"""REST adapter tests for `/v1/me` and bearer token handling (fake verifier, no IdP)."""

import json
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from stadtfest.adapters.inbound.rest import categories, me
from stadtfest.adapters.inbound.rest.auth import optional_principal
from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.adapters.inbound.rest.middleware import RequestContextMiddleware
from stadtfest.application.events.use_cases import ListActiveCategories
from stadtfest.application.identity.claims import ClaimMapping
from stadtfest.application.identity.ports import RegionRecord
from stadtfest.application.identity.use_cases import Authenticate, DeleteAccount, GetMe, UpdateMe
from stadtfest.bootstrap.logging import configure_logging
from stadtfest.bootstrap.settings import GeocodingProvider, LogFormat, Settings
from tests.fakes import (
    FakeAccountJobs,
    FakeCache,
    FakeCategoryCatalog,
    FakeDeletedAccounts,
    FakeIdpAdmin,
    FakeRegionDirectory,
    FakeTokenVerifier,
    FakeUserRepository,
)
from tests.settings_values import TEST_STORAGE

USER_TOKEN = "user-token"
MODERATOR_TOKEN = "moderator-token"
OSTALB = RegionRecord(uuid4(), "ostalb", "Ostalbkreis")


@pytest.fixture
def users() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def idp() -> FakeIdpAdmin:
    return FakeIdpAdmin()


@pytest.fixture
def client(users: FakeUserRepository, idp: FakeIdpAdmin) -> TestClient:
    deleted = FakeDeletedAccounts()
    verifier = FakeTokenVerifier(
        {
            USER_TOKEN: {
                "sub": "sub-user",
                "exp": int(time.time()) + 300,
                "realm_access": {"roles": ["user"]},
                "given_name": "Lena",
                "family_name": "Beispiel",
                "email": "lena@example.test",
            },
            MODERATOR_TOKEN: {
                "sub": "sub-mod",
                "realm_access": {"roles": ["user", "moderator"]},
                "region": "ostalb",
                "given_name": "Mia",
                "family_name": "Moderatorin",
            },
        }
    )
    regions = FakeRegionDirectory({"ostalb": OSTALB})
    app = FastAPI(dependencies=[Depends(optional_principal)])
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(categories.router)
    app.include_router(me.router)
    app.state.container = SimpleNamespace(
        list_active_categories=ListActiveCategories(FakeCategoryCatalog(), FakeCache()),
        authenticate=Authenticate(verifier, ClaimMapping("realm_access.roles", "region"), deleted),
        get_me=GetMe(users, regions),
        update_me=UpdateMe(users, regions),
        delete_account=DeleteAccount(
            users, idp, FakeAccountJobs(), deleted, token_leeway_seconds=30
        ),
    )
    return TestClient(app)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_me_requires_a_token(client: TestClient) -> None:
    response = client.get("/v1/me")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_invalid_tokens(client: TestClient) -> None:
    response = client.get("/v1/me", headers=_auth("forged"))
    assert response.status_code == 401
    assert "invalid_token" in response.headers["WWW-Authenticate"]


@pytest.mark.parametrize("header", ["Basic abc", "Bearer", "Bearer   "])
def test_malformed_authorization_header_is_rejected(client: TestClient, header: str) -> None:
    assert client.get("/v1/me", headers={"Authorization": header}).status_code == 401


def test_public_endpoint_works_without_token(client: TestClient) -> None:
    assert client.get("/v1/categories").status_code == 200


def test_public_endpoint_rejects_invalid_token(client: TestClient) -> None:
    assert client.get("/v1/categories", headers=_auth("expired")).status_code == 401


def test_public_endpoint_accepts_valid_token(client: TestClient) -> None:
    assert client.get("/v1/categories", headers=_auth(USER_TOKEN)).status_code == 200


def test_get_me_creates_the_user(client: TestClient, users: FakeUserRepository) -> None:
    response = client.get("/v1/me", headers=_auth(USER_TOKEN))

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": str(users.users["sub-user"].id),
        "firstName": "Lena",
        "lastName": "Beispiel",
        "roles": ["user"],
    }
    assert "email" not in body


def test_get_me_returns_moderator_region(client: TestClient) -> None:
    body = client.get("/v1/me", headers=_auth(MODERATOR_TOKEN)).json()
    assert body["roles"] == ["user", "moderator"]
    assert body["region"] == {"id": str(OSTALB.id), "key": "ostalb", "name": "Ostalbkreis"}


def test_patch_me_updates_names(client: TestClient) -> None:
    response = client.patch(
        "/v1/me", headers=_auth(USER_TOKEN), json={"firstName": " Lena ", "lastName": "Muster"}
    )
    assert response.status_code == 200
    assert (response.json()["firstName"], response.json()["lastName"]) == ("Lena", "Muster")


@pytest.mark.parametrize(
    "body",
    [
        {"firstName": "   ", "lastName": "Muster"},
        {"firstName": "Lena"},
        {"firstName": "", "lastName": "x"},
    ],
)
def test_patch_me_validates_names(client: TestClient, body: dict[str, str]) -> None:
    response = client.patch("/v1/me", headers=_auth(USER_TOKEN), json=body)
    assert response.status_code == 422
    assert response.json()["error"] == "validation_failed"


def test_delete_me_deletes_account(
    client: TestClient, users: FakeUserRepository, idp: FakeIdpAdmin
) -> None:
    client.get("/v1/me", headers=_auth(USER_TOKEN))

    response = client.delete("/v1/me", headers=_auth(USER_TOKEN))

    assert response.status_code == 204
    assert users.users == {}
    assert idp.deleted == ["sub-user"]


def test_deleted_account_is_not_recreated_with_a_still_valid_token(
    client: TestClient, users: FakeUserRepository
) -> None:
    client.get("/v1/me", headers=_auth(USER_TOKEN))
    client.delete("/v1/me", headers=_auth(USER_TOKEN))

    response = client.get("/v1/me", headers=_auth(USER_TOKEN))

    assert response.status_code == 401
    assert users.users == {}


def test_tokens_and_names_are_never_logged(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging(
        Settings(
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",
            redis_url="redis://localhost:6379/0",
            log_format=LogFormat.JSON,
            geocoding_provider=GeocodingProvider.FAKE,
            **TEST_STORAGE,  # type: ignore[arg-type]
        )
    )
    capsys.readouterr()

    client.get("/v1/me", headers=_auth(USER_TOKEN))
    client.get("/v1/me", headers=_auth("forged-secret-token"))

    output = capsys.readouterr().out
    for fragment in (USER_TOKEN, "forged-secret-token", "Lena", "Beispiel", "lena@example.test"):
        assert fragment not in output
    lines = [json.loads(line) for line in output.strip().splitlines()]
    assert [line["status"] for line in lines if line["event"] == "request"] == [200, 401]


def test_method_not_allowed_lists_all_methods_of_the_path(client: TestClient) -> None:
    response = client.put("/v1/me", json={})
    assert response.status_code == 405
    assert response.headers["allow"] == "DELETE, GET, PATCH"
