"""Parsing and validation of `Authorization: Bearer` headers (flow B2/B3).

REST and MCP use the same rules: no header means a guest, a malformed header or an
invalid token is rejected. Token validation itself is the `Authenticate` use case.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from stadtfest.application.identity.ports import InvalidTokenError
from stadtfest.domain.identity.principal import Principal

Authenticator = Callable[[str], Awaitable[Principal]]
"""The `Authenticate` use case: token -> principal."""


def bearer_token(header: str | None) -> str | None:
    """Return the token of an `Authorization` header, or None without a header.

    Args:
        header: Value of the `Authorization` header, if any.

    Returns:
        The token, or None if the header is missing.

    Raises:
        InvalidTokenError: If the header is not `Bearer <token>`.
    """
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise InvalidTokenError
    return token.strip()


async def principal_from_header(
    header: str | None, authenticate: Authenticator
) -> Principal | None:
    """Return the caller for an `Authorization` header, or None for guests.

    Raises:
        InvalidTokenError: If the header is malformed or the token is not valid.
        ServiceUnavailableError: If the IdP keys cannot be fetched.
    """
    token = bearer_token(header)
    if token is None:
        return None
    return await authenticate(token)
