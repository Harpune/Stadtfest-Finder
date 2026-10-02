"""Cover images for event queries (R08-US4): the first ready image of an event."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.sql.selectable import LateralFromClause

from stadtfest.adapters.outbound.persistence.models import EventImageRow, EventRow
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.events.views import ImageView
from stadtfest.domain.events.images import ImageStatus


def cover_lateral() -> LateralFromClause:
    """LATERAL subquery with ID and size of the event's cover; join it with `true()`."""
    return (
        select(EventImageRow.id, EventImageRow.width, EventImageRow.height)
        .where(
            EventImageRow.event_id == EventRow.id,
            EventImageRow.status == ImageStatus.READY.value,
        )
        .order_by(EventImageRow.position)
        .limit(1)
        .lateral("cover")
    )


def cover_view(row: Any, urls: ImageUrls) -> ImageView | None:  # noqa: ANN401  # SQLAlchemy Row
    """Cover of a result row selected with `cover_id`, `cover_width` and `cover_height`."""
    if row.cover_id is None:
        return None
    return urls.view(row.cover_id, row.cover_width, row.cover_height)
