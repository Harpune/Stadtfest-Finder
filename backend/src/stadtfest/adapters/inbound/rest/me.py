"""`/v1/me`: own profile and account deletion (R05)."""

from __future__ import annotations

from fastapi import APIRouter, Response

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.application.identity.use_cases import MeView
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/me", tags=["account"])


def _me(view: MeView) -> api.Me:
    region = (
        api.RegionRef(id=view.region.id, key=view.region.key, name=view.region.name)
        if view.region
        else None
    )
    return api.Me(
        id=view.id,
        first_name=view.first_name,
        last_name=view.last_name,
        roles=[role.value for role in view.roles],
        region=region,
    )


@router.get("", operation_id="getMe", response_model=api.Me, response_model_exclude_none=True)
async def get_me(deps: Deps, principal: CurrentPrincipal) -> api.Me:
    """Return the caller's profile; creates the account on the first call."""
    return _me(await deps.get_me(principal))


@router.patch("", operation_id="updateMe", response_model=api.Me, response_model_exclude_none=True)
async def update_me(deps: Deps, principal: CurrentPrincipal, body: api.UpdateMeRequest) -> api.Me:
    """Change first and last name."""
    return _me(await deps.update_me(principal, body.first_name, body.last_name))


@router.delete("", operation_id="deleteMe", status_code=204)
async def delete_me(deps: Deps, principal: CurrentPrincipal) -> Response:
    """Delete the account and all personal data."""
    await deps.delete_account(principal)
    return Response(status_code=204)
