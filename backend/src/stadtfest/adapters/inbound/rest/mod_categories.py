"""`/v1/mod/categories`: app-wide category maintenance (R09).

Thin adapter: parse and translate; authorization and rules live in the use cases.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.application.moderation.categories import ModCategoryView
from stadtfest.domain.events.category import CategoryDraft
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/mod/categories", tags=["moderation"])


def _category(view: ModCategoryView) -> api.ModCategory:
    return api.ModCategory(
        id=view.id,
        name=view.name,
        emoji=view.emoji,
        color=view.color,
        active=view.active,
        sort_order=view.sort_order,
        event_count=view.event_count,
    )


@router.get("", operation_id="listModCategories", response_model=list[api.ModCategory])
async def list_categories(deps: Deps, principal: CurrentPrincipal) -> list[api.ModCategory]:
    """All categories including inactive ones."""
    return [_category(view) for view in await deps.list_mod_categories(principal)]


@router.post("", operation_id="createModCategory", status_code=201, response_model=api.ModCategory)
async def create_category(
    deps: Deps, principal: CurrentPrincipal, body: api.ModCategoryCreate
) -> api.ModCategory:
    """Create a category at the end of the order."""
    draft = CategoryDraft(
        name=body.name,
        emoji=body.emoji.root,
        color=body.color.root,
        active=True if body.active is None else body.active,
    )
    return _category(await deps.create_category(principal, draft))


@router.put("/order", operation_id="orderModCategories", response_model=list[api.ModCategory])
async def order_categories(
    deps: Deps, principal: CurrentPrincipal, body: api.CategoryOrderRequest
) -> list[api.ModCategory]:
    """Set the chip order."""
    return [_category(view) for view in await deps.order_categories(principal, body.ids)]


@router.patch("/{category_id}", operation_id="updateModCategory", response_model=api.ModCategory)
async def update_category(
    deps: Deps, principal: CurrentPrincipal, category_id: UUID, body: api.ModCategoryPatch
) -> api.ModCategory:
    """Change the given fields."""
    view = await deps.update_category(
        principal,
        category_id,
        name=body.name,
        emoji=body.emoji.root if body.emoji else None,
        color=body.color.root if body.color else None,
        active=body.active,
    )
    return _category(view)


@router.delete(
    "/{category_id}", operation_id="deleteModCategory", response_model=api.CategoryDeleted
)
async def delete_category(
    deps: Deps,
    principal: CurrentPrincipal,
    category_id: UUID,
    replacement_id: Annotated[UUID | None, Query(alias="replacementId")] = None,
) -> api.CategoryDeleted:
    """Delete the category, moving its events to the replacement."""
    result = await deps.delete_category(principal, category_id, replacement_id)
    return api.CategoryDeleted(
        moved_events=result.moved_events, replacement_id=result.replacement_id
    )
