"""Geocoding via a self-hosted Nominatim instance (ADR 0006)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from stadtfest.application.geocoding.ports import GeocodingUnavailableError, Place, PlaceKind
from stadtfest.domain.events.geo import GeoPoint, PostalCode

_CITY_KEYS = ("city", "town", "village", "municipality", "suburb", "hamlet")
_CITY_TYPES = frozenset({"city", "town", "village", "municipality", "hamlet", "suburb"})


def _city(address: dict[str, str]) -> str:
    for key in _CITY_KEYS:
        if address.get(key):
            return address[key]
    return address.get("county", "")


def _to_place(item: dict[str, Any], *, postcode_query: bool) -> Place | None:  # JSON
    address: dict[str, str] = item.get("address") or {}
    try:
        location = GeoPoint(float(item["lat"]), float(item["lon"]))
    except (KeyError, TypeError, ValueError):
        return None
    city = _city(address)
    postcode = address.get("postcode")
    postal_code = postcode if postcode and PostalCode.is_valid(postcode) else None
    address_type = item.get("addresstype") or item.get("type") or ""

    if postcode_query or address_type == "postcode":
        kind = PlaceKind.POSTCODE
        label = f"{postal_code} {city}".strip() if postal_code else city
    elif address_type in _CITY_TYPES:
        kind = PlaceKind.CITY
        label = city or str(item.get("name", ""))
    else:
        kind = PlaceKind.ADDRESS
        street = " ".join(filter(None, (address.get("road"), address.get("house_number"))))
        locality = " ".join(filter(None, (postal_code, city)))
        label = ", ".join(filter(None, (street, locality))) or str(item.get("display_name", ""))
    if not city and not label:
        return None
    return Place(
        label=label, city=city or label, location=location, kind=kind, postal_code=postal_code
    )


class NominatimGeocoding:
    """Implements `GeocodingPort` against the Nominatim HTTP API (Germany only)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Create the adapter.

        Args:
            client: HTTP client with `base_url` set to the Nominatim instance, a timeout and a
                User-Agent identifying this service.
        """
        self._client = client

    async def search(self, query: str, limit: int) -> list[Place]:
        """Search by ZIP code (structured) or free text."""
        postcode_query = PostalCode.is_valid(query.strip())
        params: dict[str, str | int] = {
            "format": "jsonv2",
            "addressdetails": 1,
            "countrycodes": "de",
            "limit": limit,
        }
        if postcode_query:
            params.update({"postalcode": query.strip(), "country": "de"})
            params.pop("countrycodes")
        else:
            params["q"] = query
        items = await self._get("/search", params)
        if not isinstance(items, list):
            return []
        places = [_to_place(item, postcode_query=postcode_query) for item in items]
        return [place for place in places if place is not None]

    async def reverse(self, location: GeoPoint) -> Place | None:
        """Resolve a coordinate to a place."""
        item = await self._get(
            "/reverse",
            {
                "format": "jsonv2",
                "addressdetails": 1,
                "lat": location.lat,
                "lon": location.lon,
                "zoom": 18,
            },
        )
        if not isinstance(item, dict) or "error" in item:
            return None
        country = (item.get("address") or {}).get("country_code")
        if country and country != "de":
            return None
        place = _to_place(item, postcode_query=False)
        if place is None:
            return None
        label = f"{place.postal_code} {place.city}".strip() if place.postal_code else place.city
        address: dict[str, str] = item.get("address") or {}
        road = address.get("road") or address.get("pedestrian") or address.get("square")
        street = " ".join(filter(None, (road, address.get("house_number")))) or None
        return Place(
            label=label,
            city=place.city,
            location=place.location,
            kind=PlaceKind.POSTCODE if place.postal_code else PlaceKind.CITY,
            postal_code=place.postal_code,
            street=street,
        )

    async def _get(self, path: str, params: Mapping[str, str | int | float]) -> Any:  # noqa: ANN401  # JSON
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GeocodingUnavailableError from exc


def create_nominatim_client(base_url: str, timeout_seconds: float) -> httpx.AsyncClient:
    """Create the HTTP client for Nominatim."""
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout_seconds,
        headers={"User-Agent": "stadtfest-finder-backend/0.1 (self-hosted)"},
    )
