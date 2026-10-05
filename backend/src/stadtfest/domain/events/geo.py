"""Geographic value objects."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

_POSTAL_CODE = re.compile(r"^[0-9]{5}$")
_EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True, slots=True)
class GeoPoint:
    """A WGS84 coordinate."""

    lat: float
    lon: float

    def __post_init__(self) -> None:
        """Validate the coordinate range."""
        if not -90 <= self.lat <= 90:
            raise ValueError("latitude out of range")
        if not -180 <= self.lon <= 180:
            raise ValueError("longitude out of range")

    def rounded(self, decimals: int) -> GeoPoint:
        """Return the point rounded to `decimals` places (for cache keys, never stored)."""
        return GeoPoint(round(self.lat, decimals), round(self.lon, decimals))

    def distance_km(self, other: GeoPoint) -> float:
        """Great-circle distance in kilometers (haversine, mean earth radius)."""
        lat1, lat2 = math.radians(self.lat), math.radians(other.lat)
        dlat = lat2 - lat1
        dlon = math.radians(other.lon - self.lon)
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """A map viewport given as south-west and north-east corners."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def __post_init__(self) -> None:
        """Validate ranges and corner order."""
        GeoPoint(self.min_lat, self.min_lon)
        GeoPoint(self.max_lat, self.max_lon)
        if self.min_lon > self.max_lon or self.min_lat > self.max_lat:
            raise ValueError("bounding box corners are in the wrong order")

    @property
    def center(self) -> GeoPoint:
        """The center of the box."""
        return GeoPoint((self.min_lat + self.max_lat) / 2, (self.min_lon + self.max_lon) / 2)


@dataclass(frozen=True, slots=True)
class PostalCode:
    """A German postal code (5 digits)."""

    value: str

    def __post_init__(self) -> None:
        """Validate the format."""
        if not _POSTAL_CODE.match(self.value):
            raise ValueError("postal code must have exactly 5 digits")

    @staticmethod
    def is_valid(value: str) -> bool:
        """Return True if `value` is a well-formed postal code."""
        return bool(_POSTAL_CODE.match(value))

    def __str__(self) -> str:
        """Return the postal code as text."""
        return self.value
