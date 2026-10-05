"""Bearer token handling for the REST adapter (flow B2/B3).

Every route validates a present token, including public ones: an invalid token yields `401`
so the client refreshes it. Authorization (roles) is checked in use cases.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.application.identity.ports import InvalidTokenError
from stadtfest.domain.identity.principal import Principal

_CHALLENGE = {"WWW-Authenticate": "Bearer"}
_INVALID_TOKEN_CHALLENGE = {"WWW-Authenticate": 'Bearer error="invalid_token"'}


async def optional_principal(request: Request, deps: Deps) -> Principal | None:
    """Return the caller if a bearer token is present, else None.

    Raises:
        HTTPException: 401 if a token is present but not valid.
    """
    header = request.headers.get("authorization")
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, headers=_INVALID_TOKEN_CHALLENGE)
    try:
        return await deps.authenticate(token.strip())
    except InvalidTokenError:
        raise HTTPException(401, headers=_INVALID_TOKEN_CHALLENGE) from None


async def require_principal(
    principal: Annotated[Principal | None, Depends(optional_principal)],
) -> Principal:
    """Return the caller of a protected endpoint.

    Raises:
        HTTPException: 401 without token.
    """
    if principal is None:
        raise HTTPException(401, headers=_CHALLENGE)
    return principal


CurrentPrincipal = Annotated[Principal, Depends(require_principal)]
