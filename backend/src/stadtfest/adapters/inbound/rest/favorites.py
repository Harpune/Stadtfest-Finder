"""`/v1/me/favorites`: favorites of the signed-in user (R06)."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Response

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.adapters.inbound.rest.events import summary_fields
from stadtfest.application.collections.ports import FavoriteView
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/me/favorites", tags=["favorites"])


def _entry(favorite: FavoriteView) -> api.FavoriteEntry:
    return api.FavoriteEntry(
        **summary_fields(favorite.event),
        category_name=favorite.category_name,
        emoji=favorite.emoji,
        favorited_at=favorite.favorited_at,
    )


@router.get("", operation_id="listFavorites", response_model=api.FavoriteList)
async def list_favorites(
    deps: Deps,
    principal: CurrentPrincipal,
    include: Annotated[Literal["past"] | None, Query()] = None,
) -> api.FavoriteList:
    """Return the caller's favorites, ordered by start date."""
    favorites = await deps.list_favorites(principal, include_past=include == "past")
    return api.FavoriteList(items=[_entry(favorite) for favorite in favorites])


@router.put("/{event_id}", operation_id="addFavorite", status_code=204)
async def add_favorite(deps: Deps, principal: CurrentPrincipal, event_id: UUID) -> Response:
    """Mark the event as favorite (idempotent)."""
    await deps.add_favorite(principal, event_id)
    return Response(status_code=204)


@router.delete("/{event_id}", operation_id="removeFavorite", status_code=204)
async def remove_favorite(deps: Deps, principal: CurrentPrincipal, event_id: UUID) -> Response:
    """Remove the event from the favorites (idempotent)."""
    await deps.remove_favorite(principal, event_id)
    return Response(status_code=204)
