"""JWT validation against a locally signed JWKS (no IdP needed)."""

import json
import time
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from stadtfest.adapters.outbound.auth import jwks as jwks_module
from stadtfest.adapters.outbound.auth.jwks import JwksTokenVerifier
from stadtfest.application.identity.ports import IdpUnavailableError, InvalidTokenError

ISSUER = "http://idp.test/realms/stadtfest"
AUDIENCE = "stadtfest-api"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"


class Idp:
    """Serves a mutable JWKS and the OpenID discovery document."""

    def __init__(self) -> None:
        self.rsa = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.ec = ec.generate_private_key(ec.SECP256R1())
        self.keys: list[dict[str, Any]] = [self.jwk(self.rsa, "rsa-1"), self.jwk(self.ec, "ec-1")]
        self.requests: list[str] = []
        self.down = False

    @staticmethod
    def jwk(key: Any, kid: str) -> dict[str, Any]:
        if isinstance(key, rsa.RSAPrivateKey):
            data = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
            data["alg"] = "RS256"
        else:
            data = json.loads(ECAlgorithm.to_jwk(key.public_key()))
            data["alg"] = "ES256"
        data.update(kid=kid, use="sig")
        return data

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        if self.down:
            return httpx.Response(503)
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(200, json={"issuer": ISSUER, "jwks_uri": JWKS_URL})
        return httpx.Response(200, json={"keys": self.keys})


def _claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": "user-1",
        "iss": ISSUER,
        "aud": [AUDIENCE, "account"],
        "iat": now,
        "nbf": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return {key: value for key, value in claims.items() if value is not None}


def _sign(key: Any, kid: str, alg: str = "RS256", **overrides: Any) -> str:
    return jwt.encode(_claims(**overrides), key, algorithm=alg, headers={"kid": kid})


@pytest.fixture
def idp() -> Idp:
    return Idp()


def _verifier(idp: Idp, *, discover: bool = False) -> JwksTokenVerifier:
    http = httpx.AsyncClient(transport=httpx.MockTransport(idp.handler))
    return JwksTokenVerifier(
        http, ISSUER, AUDIENCE, jwks_url=None if discover else JWKS_URL, leeway_seconds=0
    )


async def test_valid_rs256_token_is_accepted(idp: Idp) -> None:
    claims = await _verifier(idp).verify(_sign(idp.rsa, "rsa-1"))
    assert claims["sub"] == "user-1"


async def test_valid_es256_token_is_accepted(idp: Idp) -> None:
    claims = await _verifier(idp).verify(_sign(idp.ec, "ec-1", alg="ES256"))
    assert claims["sub"] == "user-1"


async def test_jwks_url_is_discovered_from_issuer(idp: Idp) -> None:
    await _verifier(idp, discover=True).verify(_sign(idp.rsa, "rsa-1"))
    assert idp.requests == [f"{ISSUER}/.well-known/openid-configuration", JWKS_URL]


async def test_keys_are_cached(idp: Idp) -> None:
    verifier = _verifier(idp)
    await verifier.verify(_sign(idp.rsa, "rsa-1"))
    await verifier.verify(_sign(idp.rsa, "rsa-1"))
    assert idp.requests == [JWKS_URL]


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 10},
        {"nbf": int(time.time()) + 600},
        {"aud": "other-api"},
        {"iss": "http://evil.test/realms/stadtfest"},
        {"exp": None},
        {"sub": None},
    ],
    ids=["expired", "not-yet-valid", "wrong-audience", "wrong-issuer", "no-exp", "no-sub"],
)
async def test_invalid_claims_are_rejected(idp: Idp, overrides: dict[str, Any]) -> None:
    with pytest.raises(InvalidTokenError):
        await _verifier(idp).verify(_sign(idp.rsa, "rsa-1", **overrides))


async def test_token_signed_with_foreign_key_is_rejected(idp: Idp) -> None:
    foreign = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(InvalidTokenError):
        await _verifier(idp).verify(_sign(foreign, "rsa-1"))


async def test_hs256_token_is_rejected(idp: Idp) -> None:
    token = jwt.encode(_claims(), "shared-secret-" * 3, algorithm="HS256", headers={"kid": "rsa-1"})
    with pytest.raises(InvalidTokenError):
        await _verifier(idp).verify(token)


async def test_unsigned_token_is_rejected(idp: Idp) -> None:
    token = jwt.encode(_claims(), None, algorithm="none", headers={"kid": "rsa-1"})
    with pytest.raises(InvalidTokenError):
        await _verifier(idp).verify(token)


async def test_algorithm_must_match_key_type(idp: Idp) -> None:
    with pytest.raises(InvalidTokenError):
        await _verifier(idp).verify(_sign(idp.ec, "rsa-1", alg="ES256"))


@pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b.c"])
async def test_malformed_token_is_rejected(idp: Idp, token: str) -> None:
    with pytest.raises(InvalidTokenError):
        await _verifier(idp).verify(token)


async def test_rotated_key_is_loaded_on_unknown_kid(
    idp: Idp, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _verifier(idp)
    await verifier.verify(_sign(idp.rsa, "rsa-1"))
    monkeypatch.setattr(jwks_module, "MIN_REFRESH_INTERVAL_SECONDS", 0.0)
    rotated = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    idp.keys = [idp.jwk(rotated, "rsa-2")]

    claims = await verifier.verify(_sign(rotated, "rsa-2"))

    assert claims["sub"] == "user-1"
    assert idp.requests == [JWKS_URL, JWKS_URL]


async def test_unknown_kids_do_not_hammer_the_idp(idp: Idp) -> None:
    verifier = _verifier(idp)
    await verifier.verify(_sign(idp.rsa, "rsa-1"))
    for _ in range(3):
        with pytest.raises(InvalidTokenError):
            await verifier.verify(_sign(idp.rsa, "unknown"))
    assert idp.requests == [JWKS_URL]


async def test_unreachable_jwks_is_reported(idp: Idp) -> None:
    idp.down = True
    with pytest.raises(IdpUnavailableError):
        await _verifier(idp).verify(_sign(idp.rsa, "rsa-1"))
