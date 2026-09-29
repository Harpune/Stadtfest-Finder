"""Access token validation against the IdP's JWKS (flow B3)."""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt

from stadtfest.application.identity.ports import Claims, IdpUnavailableError, InvalidTokenError

ALLOWED_ALGORITHMS = frozenset({"RS256", "ES256"})
_KEY_TYPES = {"RS256": "RSA", "ES256": "EC"}
# Unknown `kid`s trigger a reload (key rotation), but at most this often (DoS protection).
MIN_REFRESH_INTERVAL_SECONDS = 30.0


class JwksTokenVerifier:
    """Validate JWTs: signature (RS256/ES256 via JWKS), `iss`, `aud`, `exp`, `nbf`.

    Keys are cached in memory and reloaded when a token references an unknown `kid`.
    Without an explicit JWKS URL, it is discovered from the issuer's OpenID configuration.
    """

    def __init__(
        self,
        http: httpx.AsyncClient,
        issuer: str,
        audience: str,
        jwks_url: str | None = None,
        leeway_seconds: int = 30,
    ) -> None:
        """Create the verifier.

        Args:
            http: HTTP client for JWKS and discovery requests.
            issuer: Expected `iss` claim, e.g. `http://localhost:58080/realms/stadtfest`.
            audience: Expected `aud` claim, e.g. `stadtfest-api`.
            jwks_url: JWKS endpoint; discovered from the issuer if omitted.
            leeway_seconds: Tolerated clock skew for `exp` and `nbf`.
        """
        self._http = http
        self._issuer = issuer
        self._audience = audience
        self._jwks_url = jwks_url
        self._leeway = leeway_seconds
        self._keys: dict[str, jwt.PyJWK] = {}
        self._last_refresh: float | None = None

    async def verify(self, token: str) -> Claims:
        """Validate the token and return its claims.

        Raises:
            InvalidTokenError: If the token is not valid.
            IdpUnavailableError: If the keys cannot be fetched.
        """
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            raise InvalidTokenError from None
        algorithm = header.get("alg")
        kid = header.get("kid")
        if algorithm not in ALLOWED_ALGORITHMS or not isinstance(kid, str):
            raise InvalidTokenError
        key = await self._key(kid)
        if key is None or key.key_type != _KEY_TYPES[algorithm]:
            raise InvalidTokenError
        try:
            claims: dict[str, Any] = jwt.decode(  # JSON claims
                token,
                key=key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError:
            raise InvalidTokenError from None
        return claims

    async def _key(self, kid: str) -> jwt.PyJWK | None:
        if kid in self._keys:
            return self._keys[kid]
        now = time.monotonic()
        if (
            self._last_refresh is not None
            and now - self._last_refresh < MIN_REFRESH_INTERVAL_SECONDS
        ):
            return None
        await self._refresh()
        return self._keys.get(kid)

    async def _refresh(self) -> None:
        try:
            url = self._jwks_url or await self._discover_jwks_url()
            response = await self._http.get(url)
            response.raise_for_status()
            key_set = jwt.PyJWKSet.from_dict(response.json())
        except (httpx.HTTPError, ValueError, jwt.PyJWTError):
            raise IdpUnavailableError from None
        self._keys = {
            key.key_id: key
            for key in key_set.keys
            if key.key_id and key.public_key_use in (None, "sig")
        }
        self._last_refresh = time.monotonic()

    async def _discover_jwks_url(self) -> str:
        response = await self._http.get(
            self._issuer.rstrip("/") + "/.well-known/openid-configuration"
        )
        response.raise_for_status()
        jwks_uri = response.json().get("jwks_uri")
        if not isinstance(jwks_uri, str):
            raise ValueError("jwks_uri missing")
        self._jwks_url = jwks_uri
        return jwks_uri
