"""Read models returned by the events use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import GeoPoint


@dataclass(frozen=True, slots=True)
class CategoryView:
    """Public category."""

    id: UUID
    name: str
    emoji: str
    color: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class ImageView:
    """Image variants (filled from R08 on)."""

    url: str
    thumb_url: str
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True, slots=True)
class EventSummaryView:
    """Event in lists, carousel and map."""

    id: UUID
    name: str
    short_name: str
    status: EventStatus
    start_date: date
    end_date: date
    place: str
    city: str
    location: GeoPoint
    category_id: UUID
    distance_km: float | None = None
    cover_image: ImageView | None = None


@dataclass(frozen=True, slots=True)
class ProgramItemView:
    """Program entry."""

    date: date
    time_label: str
    title: str
    subtitle: str | None


@dataclass(frozen=True, slots=True)
class EventDetailView:
    """Full public event detail."""

    id: UUID
    name: str
    short_name: str
    status: EventStatus
    cancel_reason: str | None
    category: CategoryView
    start_date: date
    end_date: date
    opening_hours: tuple[str, ...]
    price: str | None
    place: str
    address: str
    city: str
    postal_code: str
    location: GeoPoint
    description: str | None
    program: tuple[ProgramItemView, ...]
    transit: str | None
    parking: str | None
    website_url: str | None
    images: tuple[ImageView, ...] = field(default=())
    distance_km: float | None = None


@dataclass(frozen=True, slots=True)
class EventPageView:
    """One page of search results."""

    items: tuple[EventSummaryView, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class EventCountView:
    """Counts for the filter button and the category chips."""

    total: int
    by_category: dict[UUID, int]
