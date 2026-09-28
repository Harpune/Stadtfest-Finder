"""Search criteria and keyset cursor for the public event search."""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass, field, replace
from datetime import date
from uuid import UUID

from stadtfest.domain.events.geo import BoundingBox, GeoPoint
from stadtfest.domain.events.time_filter import DateRange, TimeFilter

DEFAULT_RADIUS_KM = 150
MIN_RADIUS_KM = 10
MAX_RADIUS_KM = 300
MIN_QUERY_LENGTH = 2


@dataclass(frozen=True, slots=True)
class SearchFilter:
    """Filters as requested by the client (before resolving "today")."""

    bbox: BoundingBox | None = None
    reference: GeoPoint | None = None
    radius_km: int = DEFAULT_RADIUS_KM
    time: TimeFilter = field(default_factory=TimeFilter)
    category_ids: frozenset[UUID] | None = None
    text: str | None = None

    def __post_init__(self) -> None:
        """Validate the radius and the text length."""
        if not MIN_RADIUS_KM <= self.radius_km <= MAX_RADIUS_KM:
            raise ValueError("radius out of range")
        if self.text is not None:
            if len(self.text.strip()) < MIN_QUERY_LENGTH:
                raise ValueError("search text too short")
            if any(ord(char) < 32 for char in self.text):  # control characters
                raise ValueError("search text contains control characters")

    @property
    def distance_reference(self) -> GeoPoint | None:
        """Point distances are measured from: the reference, else the bbox center."""
        if self.reference is not None:
            return self.reference
        return self.bbox.center if self.bbox is not None else None

    def without_categories(self) -> SearchFilter:
        """Return the same filter without the category restriction (for chip counts)."""
        return replace(self, category_ids=None)


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    """Filter resolved against the current day; consumed by the catalog port."""

    filter: SearchFilter
    today: date
    windows: tuple[DateRange, ...] | None

    @classmethod
    def resolve(cls, search_filter: SearchFilter, today: date) -> SearchCriteria:
        """Resolve the time filter for `today` (Europe/Berlin)."""
        return cls(search_filter, today, search_filter.time.windows(today))


@dataclass(frozen=True, slots=True)
class PageCursor:
    """Keyset position: (running first, start date, name, id)."""

    upcoming: bool
    start_date: date
    name: str
    id: UUID

    def encode(self) -> str:
        """Return the opaque cursor string."""
        payload = [int(self.upcoming), self.start_date.isoformat(), self.name, str(self.id)]
        raw = json.dumps(payload, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @classmethod
    def decode(cls, value: str) -> PageCursor:
        """Parse a cursor created by `encode`.

        Raises:
            ValueError: If the cursor is malformed.
        """
        try:
            raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
            upcoming, start, name, event_id = json.loads(raw)
            if not isinstance(name, str) or "\x00" in name:
                raise ValueError("invalid cursor name")
            return cls(bool(upcoming), date.fromisoformat(start), name, UUID(event_id))
        except (binascii.Error, ValueError, TypeError, UnicodeDecodeError) as exc:
            raise ValueError("invalid cursor") from exc
