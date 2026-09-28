"""Use cases of the public event catalog (flow A)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from stadtfest.application.events import codec
from stadtfest.application.events.criteria import PageCursor, SearchCriteria, SearchFilter
from stadtfest.application.events.ports import CategoryCatalog, EventCatalog
from stadtfest.application.events.views import (
    CategoryView,
    EventCountView,
    EventDetailView,
    EventPageView,
)
from stadtfest.application.shared.errors import InvalidInputError, NotFoundError
from stadtfest.application.shared.ports import CachePort, Clock
from stadtfest.domain.events.geo import GeoPoint

# Cache namespaces. Bumping a generation invalidates every key of that namespace.
CATALOG_NAMESPACE = "catalog"
CATEGORIES_NAMESPACE = "categories"

SEARCH_TTL_SECONDS = 5 * 60
CATEGORIES_TTL_SECONDS = 60 * 60
MAX_PAGE_SIZE = 500


def _filter_cache_key(search_filter: SearchFilter, today: str) -> str:
    """Stable hash of the normalized filter. Coordinates are rounded (never stored exactly)."""
    reference = search_filter.reference.rounded(2) if search_filter.reference else None
    bbox = search_filter.bbox
    normalized = {
        "today": today,
        "bbox": (
            [round(v, 3) for v in (bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat)]
            if bbox
            else None
        ),
        "ref": [reference.lat, reference.lon] if reference else None,
        "radius": search_filter.radius_km,
        "when": search_filter.time.kind.value,
        "months": sorted(str(m) for m in search_filter.time.months),
        "cats": sorted(str(c) for c in search_filter.category_ids)
        if search_filter.category_ids is not None
        else None,
        "q": search_filter.text.strip().lower() if search_filter.text else None,
    }
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()


class SearchEvents:
    """Search listed events for map and list, with a short-lived cache for guests."""

    def __init__(self, catalog: EventCatalog, cache: CachePort, clock: Clock) -> None:
        """Create the use case."""
        self._catalog = catalog
        self._cache = cache
        self._clock = clock

    async def __call__(
        self,
        search_filter: SearchFilter,
        cursor: str | None = None,
        limit: int = 50,
        *,
        cacheable: bool = True,
    ) -> EventPageView:
        """Return one page of events.

        Args:
            search_filter: Requested filters.
            cursor: Cursor of the previous page.
            limit: Page size (1-500).
            cacheable: False for authenticated requests (never cache user-specific data).

        Returns:
            The page with a cursor for the next one.

        Raises:
            InvalidInputError: If the cursor is malformed.
        """
        try:
            after = PageCursor.decode(cursor) if cursor else None
        except ValueError:
            raise InvalidInputError({"cursor": "invalid"}) from None
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        today = self._clock.today()

        key: str | None = None
        if cacheable:
            generation = await self._cache.generation(CATALOG_NAMESPACE)
            digest = _filter_cache_key(search_filter, today.isoformat())
            key = f"events:search:{generation}:{digest}:{cursor or ''}:{limit}"
            cached = await self._cache.get_json(key)
            if isinstance(cached, dict):
                return codec.page_from_json(cached)

        criteria = SearchCriteria.resolve(search_filter, today)
        rows = await self._catalog.search(criteria, after, limit + 1)
        items = tuple(rows[:limit])
        next_cursor = None
        if len(rows) > limit:
            last = items[-1]
            next_cursor = PageCursor(
                upcoming=last.start_date > today,
                start_date=last.start_date,
                name=last.name,
                id=last.id,
            ).encode()
        page = EventPageView(items=items, next_cursor=next_cursor)

        if key is not None:
            await self._cache.set_json(key, codec.page_to_json(page), SEARCH_TTL_SECONDS)
        return page


class CountEvents:
    """Count listed events for the filter preview and the category chips."""

    def __init__(self, catalog: EventCatalog, cache: CachePort, clock: Clock) -> None:
        """Create the use case."""
        self._catalog = catalog
        self._cache = cache
        self._clock = clock

    async def __call__(
        self, search_filter: SearchFilter, *, cacheable: bool = True
    ) -> EventCountView:
        """Return the counts for the filter."""
        today = self._clock.today()
        key: str | None = None
        if cacheable:
            generation = await self._cache.generation(CATALOG_NAMESPACE)
            digest = _filter_cache_key(search_filter, today.isoformat())
            key = f"events:count:{generation}:{digest}"
            cached = await self._cache.get_json(key)
            if isinstance(cached, dict):
                return codec.count_from_json(cached)

        counts = await self._catalog.count(SearchCriteria.resolve(search_filter, today))
        if key is not None:
            await self._cache.set_json(key, codec.count_to_json(counts), SEARCH_TTL_SECONDS)
        return counts


@dataclass(frozen=True, slots=True)
class ActiveCategories:
    """Active categories with a version tag for HTTP caching."""

    categories: list[CategoryView]
    etag: str


class ListActiveCategories:
    """Return active categories in moderation order (cached 1 h)."""

    def __init__(self, categories: CategoryCatalog, cache: CachePort) -> None:
        """Create the use case."""
        self._categories = categories
        self._cache = cache

    async def __call__(self) -> ActiveCategories:
        """Return the categories and their ETag."""
        generation = await self._cache.generation(CATEGORIES_NAMESPACE)
        key = f"categories:active:{generation}"
        cached = await self._cache.get_json(key)
        if isinstance(cached, list):
            encoded = cached
        else:
            encoded = codec.categories_to_json(await self._categories.list_active())
            await self._cache.set_json(key, encoded, CATEGORIES_TTL_SECONDS)
        etag = hashlib.sha256(json.dumps(encoded, sort_keys=True).encode()).hexdigest()[:32]
        return ActiveCategories(categories=codec.categories_from_json(encoded), etag=f'"{etag}"')


class GetPublicEvent:
    """Return the detail of a published or cancelled event."""

    def __init__(self, catalog: EventCatalog) -> None:
        """Create the use case."""
        self._catalog = catalog

    async def __call__(self, event_id: UUID, reference: GeoPoint | None = None) -> EventDetailView:
        """Return the event.

        Raises:
            NotFoundError: If the event does not exist, is a draft or was deleted.
        """
        event = await self._catalog.get_public(event_id, reference)
        if event is None:
            raise NotFoundError(str(event_id))
        return event
