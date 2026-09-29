"""Real login roundtrip against Keycloak (ADR 0003): token -> JWKS validation -> principal.

Uses the realm from infra/dev/keycloak and its `stadtfest-tests` client (password grant,
dev only). Also covers the account deletion via the Keycloak Admin API.
"""

import time
from collections.abc import Iterator

import httpx
import pytest
from testcontainers.core.container import DockerContainer

from stadtfest.adapters.outbound.auth.idp_admin import KeycloakIdpAdmin
from stadtfest.adapters.outbound.auth.jwks import JwksTokenVerifier
from stadtfest.application.identity.claims import ClaimMapping, principal_from_claims
from stadtfest.application.identity.ports import InvalidTokenError
from stadtfest.domain.identity.principal import Role
from tests.conftest import REPO_ROOT

pytestmark = pytest.mark.integration

KEYCLOAK_IMAGE = "quay.io/keycloak/keycloak:26.4"  # same as infra/compose.dev.yaml
REALM_FILE = REPO_ROOT / "infra" / "dev" / "keycloak" / "stadtfest-realm.json"
PASSWORD = "stadtfest-dev"  # dev-only test users from the realm file


@pytest.fixture(scope="module")
def issuer() -> Iterator[str]:
    container = (
        DockerContainer(KEYCLOAK_IMAGE)
        .with_command("start-dev --import-realm")
        .with_env("KC_BOOTSTRAP_ADMIN_USERNAME", "admin")
        .with_env("KC_BOOTSTRAP_ADMIN_PASSWORD", "admin")
        .with_exposed_ports(8080)
        .with_volume_mapping(
            str(REALM_FILE), "/opt/keycloak/data/import/stadtfest-realm.json", "ro"
        )
    )
    with container:
        base = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"
        realm = f"{base}/realms/stadtfest"
        deadline = time.monotonic() + 240
        while True:
            try:
                if httpx.get(f"{realm}/.well-known/openid-configuration").is_success:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError("Keycloak did not start")
            time.sleep(2)
        yield realm


def _password_grant(issuer: str, username: str) -> httpx.Response:
    return httpx.post(
        f"{issuer}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "stadtfest-tests",
            "username": username,
            "password": PASSWORD,
            "scope": "openid",
        },
    )


async def test_moderator_token_is_validated_and_mapped(issuer: str) -> None:
    response = _password_grant(issuer, "moderator@example.test")
    response.raise_for_status()
    async with httpx.AsyncClient() as http:
        verifier = JwksTokenVerifier(http, issuer, "stadtfest-api")
        claims = await verifier.verify(response.json()["access_token"])

    principal = principal_from_claims(claims, ClaimMapping("realm_access.roles", "region"))
    assert principal.roles == {Role.USER, Role.MODERATOR}
    assert principal.region_key == "ostalb"
    assert (principal.given_name, principal.family_name) == ("Mia", "Moderatorin")


async def test_id_token_is_not_accepted_as_access_token(issuer: str) -> None:
    response = _password_grant(issuer, "nutzer@example.test")
    response.raise_for_status()
    async with httpx.AsyncClient() as http:
        verifier = JwksTokenVerifier(http, issuer, "stadtfest-api")
        with pytest.raises(InvalidTokenError):  # audience is the client, not the API
            await verifier.verify(response.json()["id_token"])


async def test_account_deletion_removes_the_keycloak_user(issuer: str) -> None:
    response = _password_grant(issuer, "katadmin@example.test")
    response.raise_for_status()
    async with httpx.AsyncClient() as http:
        claims = await JwksTokenVerifier(http, issuer, "stadtfest-api").verify(
            response.json()["access_token"]
        )
        admin = KeycloakIdpAdmin(http, issuer, "stadtfest-admin", "stadtfest-dev-admin-secret")
        await admin.delete_user(str(claims["sub"]))
        await admin.delete_user(str(claims["sub"]))  # already deleted: still succeeds

    assert _password_grant(issuer, "katadmin@example.test").status_code == 401
