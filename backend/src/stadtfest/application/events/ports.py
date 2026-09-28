"""Outbound ports of the events context."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from stadtfest.application.events.criteria import PageCursor, SearchCriteria
from stadtfest.application.events.views import (
    CategoryView,
    EventCountView,
    EventDetailView,
    EventSummaryView,
)
from stadtfest.domain.events.geo import GeoPoint


class EventCatalog(Protocol):
    """Read access to publicly visible events."""

    async def search(
        self, criteria: SearchCriteria, after: PageCursor | None, limit: int
    ) -> list[EventSummaryView]:
        """Return up to `limit` listed events after the cursor, in public sort order."""
        ...

    async def count(self, criteria: SearchCriteria) -> EventCountView:
        """Count listed events: total with all filters, per category without category filter."""
        ...

    async def get_public(
        self, event_id: UUID, reference: GeoPoint | None
    ) -> EventDetailView | None:
        """Return a publicly accessible event (also past ones) or None."""
        ...


class CategoryCatalog(Protocol):
    """Read access to categories."""

    async def list_active(self) -> list[CategoryView]:
        """Return active categories ordered by sort order."""
        ...
