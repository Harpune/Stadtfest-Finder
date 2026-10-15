"""Shared bearer header parsing (REST and MCP, R15-US2)."""

import pytest

from stadtfest.adapters.inbound.auth.bearer import bearer_token, principal_from_header
from stadtfest.application.identity.ports import InvalidTokenError
from stadtfest.domain.identity.principal import Principal, Role


@pytest.mark.parametrize(
    ("header", "token"),
    [(None, None), ("Bearer abc", "abc"), ("bearer  abc ", "abc")],
)
def test_bearer_token(header: str | None, token: str | None) -> None:
    assert bearer_token(header) == token


@pytest.mark.parametrize("header", ["Basic abc", "Bearer", "Bearer   ", "abc"])
def test_malformed_headers_are_invalid_tokens(header: str) -> None:
    with pytest.raises(InvalidTokenError):
        bearer_token(header)


async def test_principal_from_header_authenticates_only_with_a_token() -> None:
    seen: list[str] = []

    async def authenticate(token: str) -> Principal:
        seen.append(token)
        return Principal(subject="s", roles=frozenset({Role.USER}))

    assert await principal_from_header(None, authenticate) is None
    principal = await principal_from_header("Bearer t", authenticate)
    assert principal is not None
    assert principal.subject == "s"
    assert seen == ["t"]
