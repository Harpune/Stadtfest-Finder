"""Public catalog endpoints: `/v1/events`, `/v1/events/count`, `/v1/events/{id}`."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from stadtfest.adapters.inbound.rest.auth import optional_principal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.application.events.criteria import (
    DEFAULT_RADIUS_KM,
    MAX_RADIUS_KM,
    MIN_RADIUS_KM,
    SearchFilter,
)
from stadtfest.application.events.views import (
    CategoryView,
    EventDetailView,
    EventSummaryView,
    ImageView,
)
from stadtfest.application.shared.errors import InvalidInputError
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import BoundingBox, GeoPoint
from stadtfest.domain.events.time_filter import TimeFilter, TimeFilterKind, YearMonth
from stadtfest.domain.identity.principal import Principal
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/events", tags=["events"])


def _csv(value: str | None) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()] if value else []


def _parse_filter(  # mirrors the query parameters of the spec
    bbox: str | None,
    lat: float | None,
    lon: float | None,
    radius_km: int,
    when: str,
    months: str | None,
    categories: str | None,
    q: str | None,
) -> SearchFilter:
    errors: dict[str, str] = {}

    box = None
    if bbox is not None:
        try:
            values = [float(v) for v in _csv(bbox)]
            if len(values) != 4:  # minLon,minLat,maxLon,maxLat
                raise ValueError
            box = BoundingBox(*values)
        except ValueError:
            errors["bbox"] = "invalid"

    reference = None
    if (lat is None) != (lon is None):
        errors["lat" if lat is None else "lon"] = "required_together"
    elif lat is not None and lon is not None:
        reference = GeoPoint(lat, lon)

    time_filter = TimeFilter()
    try:
        kind = TimeFilterKind(when)
        parsed_months = tuple(YearMonth.parse(m) for m in _csv(months))
        time_filter = TimeFilter(kind, parsed_months if kind is TimeFilterKind.MONTHS else ())
    except ValueError:
        errors["months"] = "invalid"

    category_ids = None
    if categories is not None:
        try:
            category_ids = frozenset(UUID(c) for c in _csv(categories))
        except ValueError:
            errors["categories"] = "invalid"

    if errors:
        raise InvalidInputError(errors)
    try:
        return SearchFilter(
            bbox=box,
            reference=reference,
            radius_km=radius_km,
            time=time_filter,
            category_ids=category_ids or None,
            text=q,
        )
    except ValueError:
        raise InvalidInputError({"q": "invalid"}) from None


def search_filter(
    bbox: Annotated[str | None, Query(max_length=200)] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[
        int, Query(alias="radiusKm", ge=MIN_RADIUS_KM, le=MAX_RADIUS_KM)
    ] = DEFAULT_RADIUS_KM,
    when: Annotated[str, Query(pattern="^(all|today|weekend|months)$")] = "all",
    months: Annotated[str | None, Query(max_length=200)] = None,
    categories: Annotated[str | None, Query(max_length=2000)] = None,
    q: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
) -> SearchFilter:
    """Parse the shared filter parameters of `searchEvents` and `countEvents`."""
    return _parse_filter(bbox, lat, lon, radius_km, when, months, categories, q)


Filter = Annotated[SearchFilter, Depends(search_filter)]


def _status(status: EventStatus) -> api.PublicEventStatus:
    # Only published and cancelled events are public (enforced by the catalog query).
    if status is EventStatus.CANCELLED:
        return api.PublicEventStatus("cancelled")
    return api.PublicEventStatus("published")


def _image(image: ImageView | None) -> api.Image | None:
    if image is None:
        return None
    return api.Image(
        url=image.url, thumb_url=image.thumb_url, width=image.width, height=image.height
    )


# Any: keyword arguments for a generated pydantic model with mixed field types.
def summary_fields(item: EventSummaryView) -> dict[str, Any]:
    """Fields of `EventSummary`, shared with schemas that extend it (`FavoriteEntry`)."""
    return {
        "id": item.id,
        "name": item.name,
        "short_name": item.short_name,
        "status": _status(item.status),
        "start_date": item.start_date,
        "end_date": item.end_date,
        "place": item.place,
        "city": item.city,
        "lat": item.location.lat,
        "lon": item.location.lon,
        "category_id": item.category_id,
        "distance_km": item.distance_km,
        "cover_image": _image(item.cover_image),
    }


def _summary(item: EventSummaryView) -> api.EventSummary:
    return api.EventSummary(**summary_fields(item))


def _category_ref(category: CategoryView) -> api.CategoryRef:
    return api.CategoryRef(
        id=category.id, name=category.name, emoji=category.emoji, color=category.color
    )


def _detail(event: EventDetailView, is_favorite: bool | None) -> api.EventDetail:
    # Not passed at all without a token, so that `isFavorite` is left out of the response.
    extra = {"is_favorite": is_favorite} if is_favorite is not None else {}
    return api.EventDetail(
        **extra,
        id=event.id,
        name=event.name,
        short_name=event.short_name,
        status=_status(event.status),
        cancel_reason=event.cancel_reason,
        category=_category_ref(event.category),
        start_date=event.start_date,
        end_date=event.end_date,
        opening_hours=list(event.opening_hours),
        price=event.price,
        place=event.place,
        address=event.address,
        city=event.city,
        postal_code=event.postal_code,
        lat=event.location.lat,
        lon=event.location.lon,
        description=event.description,
        program=[
            api.ProgramItem(
                date=item.date,
                time_label=item.time_label,
                title=item.title,
                subtitle=item.subtitle,
            )
            for item in event.program
        ],
        transit=event.transit,
        parking=event.parking,
        website_url=event.website_url,
        images=[image for image in (_image(i) for i in event.images) if image is not None],
        distance_km=event.distance_km,
    )


@router.get("", operation_id="searchEvents", response_model=api.EventPage)
async def search_events(
    deps: Deps,
    search: Filter,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> api.EventPage:
    """Search listed events for map and list."""
    page = await deps.search_events(search, cursor, limit)
    return api.EventPage(
        items=[_summary(item) for item in page.items], next_cursor=page.next_cursor
    )


@router.get("/count", operation_id="countEvents", response_model=api.EventCount)
async def count_events(deps: Deps, search: Filter) -> api.EventCount:
    """Count events for the filter preview and the category chips."""
    counts = await deps.count_events(search)
    return api.EventCount(
        total=counts.total, by_category={str(k): v for k, v in counts.by_category.items()}
    )


@router.get(
    "/{event_id}",
    operation_id="getEvent",
    response_model=api.EventDetail,
    response_model_exclude_unset=True,
)
async def get_event(
    deps: Deps,
    event_id: UUID,
    principal: Annotated[Principal | None, Depends(optional_principal)],
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> api.EventDetail:
    """Return the detail of a published or cancelled event."""
    reference = GeoPoint(lat, lon) if lat is not None and lon is not None else None
    event = await deps.get_public_event(event_id, reference)
    # `isFavorite` only with a token (R06-US1); public responses stay user-neutral.
    is_favorite = await deps.is_favorite(principal, event_id) if principal else None
    return _detail(event, is_favorite)
