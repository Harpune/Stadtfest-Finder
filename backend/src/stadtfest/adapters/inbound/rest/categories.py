"""`GET /v1/categories` with ETag-based HTTP caching."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Response
from fastapi.responses import JSONResponse

from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/categories", tags=["categories"])

CACHE_CONTROL = "public, max-age=900"


@router.get("", operation_id="listCategories", response_model=list[api.Category])
async def list_categories(
    deps: Deps,
    if_none_match: Annotated[str | None, Header()] = None,
) -> Response:
    """Return active categories; `304` if the client's ETag is current."""
    result = await deps.list_active_categories()
    headers = {"ETag": result.etag, "Cache-Control": CACHE_CONTROL}
    if if_none_match is not None and result.etag in {t.strip() for t in if_none_match.split(",")}:
        return Response(status_code=304, headers=headers)
    body = [
        api.Category(
            id=c.id, name=c.name, emoji=c.emoji, color=c.color, sort_order=c.sort_order
        ).model_dump(mode="json", by_alias=True)
        for c in result.categories
    ]
    return JSONResponse(content=body, headers=headers)
