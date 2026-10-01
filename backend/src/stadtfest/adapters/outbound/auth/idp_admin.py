"""IdP admin adapters for account deletion: Keycloak (local), Zitadel (production), fake."""

from __future__ import annotations

import logging
import time
from urllib.parse import quote

import httpx

from stadtfest.application.identity.ports import IdpUnavailableError

logger = logging.getLogger(__name__)


def _raise_for_delete(response: httpx.Response) -> None:
    # 404: the user is already gone, which is the desired end state.
    if response.status_code == httpx.codes.NOT_FOUND:
        return
    if response.is_error:
        raise IdpUnavailableError


class KeycloakIdpAdmin:
    """Keycloak Admin API with a confidential client (client credentials grant)."""

    def __init__(
        self, http: httpx.AsyncClient, issuer: str, client_id: str, client_secret: str
    ) -> None:
        """Create the adapter.

        Args:
            http: HTTP client.
            issuer: Realm URL, e.g. `http://localhost:58080/realms/stadtfest`.
            client_id: Service client with the `realm-management` role `manage-users`.
            client_secret: Secret of that client.
        """
        base, _, realm = issuer.rstrip("/").rpartition("/realms/")
        self._http = http
        self._token_url = f"{issuer.rstrip('/')}/protocol/openid-connect/token"
        self._users_url = f"{base}/admin/realms/{realm}/users"
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expires_at = 0.0

    async def delete_user(self, subject: str) -> None:
        """Delete the user; the Keycloak user ID equals the `sub` claim."""
        try:
            token = await self._access_token()
            response = await self._http.delete(
                f"{self._users_url}/{quote(subject, safe='')}",
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError:
            raise IdpUnavailableError from None
        _raise_for_delete(response)

    async def _access_token(self) -> str:
        if self._token is not None and time.monotonic() < self._token_expires_at:
            return self._token
        response = await self._http.post(
            self._token_url,
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
        )
        if response.is_error:
            raise IdpUnavailableError
        payload = response.json()
        self._token = str(payload["access_token"])
        self._token_expires_at = time.monotonic() + float(payload.get("expires_in", 60)) - 10
        return self._token


class ZitadelIdpAdmin:
    """Zitadel User API v2 with a service user's personal access token."""

    def __init__(self, http: httpx.AsyncClient, issuer: str, access_token: str) -> None:
        """Create the adapter.

        Args:
            http: HTTP client.
            issuer: Instance URL, e.g. `https://stadtfest-xyz.eu1.zitadel.cloud`.
            access_token: PAT of a service user with the role `ORG_USER_MANAGER`.
        """
        self._http = http
        self._users_url = f"{issuer.rstrip('/')}/v2/users"
        self._access_token = access_token

    async def delete_user(self, subject: str) -> None:
        """Delete the user; the Zitadel user ID equals the `sub` claim."""
        try:
            response = await self._http.delete(
                f"{self._users_url}/{quote(subject, safe='')}",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
        except httpx.HTTPError:
            raise IdpUnavailableError from None
        _raise_for_delete(response)


class FakeIdpAdmin:
    """No-op for dev and test without IdP admin credentials (not allowed in prod)."""

    async def delete_user(self, subject: str) -> None:
        """Pretend to delete the user."""
        logger.info("idp_user_deletion_skipped")
