"""Helpers to load the synthetic seed (repo-root `seed/`) in integration tests."""

from __future__ import annotations

import math
import sys
from datetime import date, timedelta

from tests.conftest import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "seed"))

from catalog import CATEGORIES, EVENTS, SeedEvent, seed_id
from load import load

__all__ = ["CATEGORIES", "EVENTS", "SeedEvent", "haversine_km", "listed", "load", "seed_id"]


def end_date(event: SeedEvent, today: date) -> date | None:
    """End date of a seed event relative to `today`."""
    if event.start is None:
        return None
    return today + timedelta(days=event.start + event.days - 1)


def start_date(event: SeedEvent, today: date) -> date | None:
    """Start date of a seed event relative to `today`."""
    return today + timedelta(days=event.start) if event.start is not None else None


def listed(today: date) -> list[SeedEvent]:
    """Seed events that must appear on map/list: published/cancelled and not ended."""
    result = []
    for event in EVENTS:
        end = end_date(event, today)
        if event.status in {"published", "cancelled"} and end is not None and end >= today:
            result.append(event)
    return result


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km (spherical approximation)."""
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))
