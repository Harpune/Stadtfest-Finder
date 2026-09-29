import httpx
import pytest

from stadtfest.adapters.outbound.auth.idp_admin import KeycloakIdpAdmin, ZitadelIdpAdmin
from stadtfest.application.identity.ports import IdpUnavailableError


class Recorder:
    def __init__(self, delete_status: int = 204) -> None:
        self.delete_status = delete_status
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "admin-at", "expires_in": 300})
        return httpx.Response(self.delete_status)


def _client(recorder: Recorder) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(recorder.handler))


async def test_keycloak_deletes_user_with_client_credentials() -> None:
    recorder = Recorder()
    admin = KeycloakIdpAdmin(
        _client(recorder), "http://kc.test/realms/stadtfest", "stadtfest-admin", "s3cret"
    )

    await admin.delete_user("abc-123")
    await admin.delete_user("def-456")

    token_request, delete_request, second_delete = recorder.requests
    assert str(token_request.url) == "http://kc.test/realms/stadtfest/protocol/openid-connect/token"
    assert b"grant_type=client_credentials" in token_request.content
    assert delete_request.method == "DELETE"
    assert str(delete_request.url) == "http://kc.test/admin/realms/stadtfest/users/abc-123"
    assert delete_request.headers["Authorization"] == "Bearer admin-at"
    assert second_delete.url.path.endswith("/def-456")  # token is reused


async def test_zitadel_deletes_user_with_pat() -> None:
    recorder = Recorder(delete_status=200)
    admin = ZitadelIdpAdmin(_client(recorder), "https://sf.eu1.zitadel.cloud/", "pat")

    await admin.delete_user("2984")

    (request,) = recorder.requests
    assert request.method == "DELETE"
    assert str(request.url) == "https://sf.eu1.zitadel.cloud/v2/users/2984"
    assert request.headers["Authorization"] == "Bearer pat"


async def test_already_deleted_user_counts_as_success() -> None:
    admin = ZitadelIdpAdmin(_client(Recorder(delete_status=404)), "https://sf.test", "pat")
    await admin.delete_user("gone")


@pytest.mark.parametrize("status", [401, 500, 503])
async def test_idp_errors_are_reported_as_unavailable(status: int) -> None:
    admin = ZitadelIdpAdmin(_client(Recorder(delete_status=status)), "https://sf.test", "pat")
    with pytest.raises(IdpUnavailableError):
        await admin.delete_user("x")


async def test_network_errors_are_reported_as_unavailable() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    http = httpx.AsyncClient(transport=httpx.MockTransport(fail))
    with pytest.raises(IdpUnavailableError):
        await KeycloakIdpAdmin(http, "http://kc.test/realms/r", "c", "s").delete_user("x")
