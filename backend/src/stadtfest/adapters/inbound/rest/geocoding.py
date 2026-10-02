"""`/v1/geocode` and `/v1/geocode/reverse` (self-hosted Nominatim behind a port)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.adapters.inbound.rest.rate_limit import RateLimit
from stadtfest.application.geocoding.ports import Place
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.generated import models as api

GEOCODE_REQUESTS_PER_SECOND = 5

router = APIRouter(
    prefix="/v1/geocode",
    tags=["geocoding"],
    dependencies=[Depends(RateLimit("geocode", GEOCODE_REQUESTS_PER_SECOND))],
)


def _result(place: Place) -> api.GeocodeResult:
    return api.GeocodeResult(
        label=place.label,
        postal_code=place.postal_code,
        city=place.city,
        lat=place.location.lat,
        lon=place.location.lon,
        kind=place.kind.value,
    )


@router.get("", operation_id="geocode", response_model=list[api.GeocodeResult])
async def geocode(
    deps: Deps,
    q: Annotated[str, Query(min_length=2, max_length=120)],
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> list[api.GeocodeResult]:
    """Suggest places for a city, ZIP code or address."""
    return [_result(place) for place in await deps.geocode(q, limit)]


@router.get("/reverse", operation_id="reverseGeocode", response_model=api.ReverseGeocodeResult)
async def reverse_geocode(
    deps: Deps,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
) -> api.ReverseGeocodeResult:
    """Resolve coordinates to postal code and place."""
    place = await deps.reverse_geocode(GeoPoint(lat, lon))
    return api.ReverseGeocodeResult(
        postal_code=place.postal_code, city=place.city, label=place.label
    )


mod_router = APIRouter(prefix="/v1/mod/geocode", tags=["moderation"])


@mod_router.get(
    "/reverse",
    operation_id="reverseGeocodeEventLocation",
    response_model=api.ReverseGeocodeResult,
)
async def reverse_geocode_event_location(
    deps: Deps,
    principal: CurrentPrincipal,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
) -> api.ReverseGeocodeResult:
    """Resolve an event pin to street, postal code and place (moderators)."""
    place = await deps.reverse_geocode_event_location(principal, GeoPoint(lat, lon))
    return api.ReverseGeocodeResult(
        street=place.street, postal_code=place.postal_code, city=place.city, label=place.label
    )
