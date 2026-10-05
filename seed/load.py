"""Load synthetic seed data into the database (`make seed`).

Idempotent: the catalog tables are emptied and refilled with deterministic IDs.
Refuses to run with ENV=prod.

Usage (from backend/): uv run python ../seed/load.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog import CATEGORIES, EVENTS, seed_id

from stadtfest.adapters.outbound.cache.redis_cache import RedisCache
from stadtfest.adapters.outbound.cache.redis_client import create_redis
from stadtfest.adapters.outbound.clock.berlin_clock import BerlinClock
from stadtfest.adapters.outbound.persistence.models import (
    CategoryRow,
    EventRow,
    ProgramItemRow,
)
from stadtfest.application.events.use_cases import (
    CATALOG_NAMESPACE,
    CATEGORIES_NAMESPACE,
)
from stadtfest.bootstrap.settings import Environment, load_settings


async def load(sessions: async_sessionmaker[AsyncSession], today: date) -> dict[str, int]:
    """Replace the catalog with the seed data.

    Args:
        sessions: Session factory.
        today: Reference day for the relative event dates.

    Returns:
        Number of inserted rows per table.
    """
    async with sessions() as session, session.begin():
        await session.execute(text("TRUNCATE event_image, program_item, event, category CASCADE"))
        for position, category in enumerate(CATEGORIES):
            session.add(
                CategoryRow(
                    id=seed_id("category", category.key),
                    name=category.name,
                    emoji=category.emoji,
                    color=category.color,
                    active=category.active,
                    sort_order=position,
                )
            )
        await session.flush()

        program_count = 0
        for event in EVENTS:
            event_id = seed_id("event", event.key)
            start = today + timedelta(days=event.start) if event.start is not None else None
            end = start + timedelta(days=event.days - 1) if start is not None else None
            location = (
                f"SRID=4326;POINT({event.lon} {event.lat})"
                if event.lat is not None and event.lon is not None
                else None
            )
            session.add(
                EventRow(
                    id=event_id,
                    name=event.name,
                    short_name=event.short_name,
                    category_id=seed_id("category", event.category) if event.category else None,
                    status=event.status,
                    start_date=start,
                    end_date=end,
                    opening_hours=list(event.opening_hours),
                    price=event.price,
                    place=event.place,
                    address=event.address,
                    city=event.city,
                    postal_code=event.postal_code,
                    location=location,
                    description=event.description,
                    transit=event.transit,
                    parking=event.parking,
                    website_url=event.website_url,
                    cancel_reason=event.cancel_reason,
                    source=event.source,
                    source_url=event.source_url,
                )
            )
            await session.flush()
            for position, item in enumerate(event.program):
                assert start is not None  # seed events with a program have dates
                session.add(
                    ProgramItemRow(
                        id=seed_id("program", f"{event.key}/{position}"),
                        event_id=event_id,
                        date=start + timedelta(days=item.day),
                        time_label=item.time_label,
                        title=item.title,
                        subtitle=item.subtitle,
                        position=position,
                    )
                )
                program_count += 1
    return {
        "category": len(CATEGORIES),
        "event": len(EVENTS),
        "program_item": program_count,
    }


async def main() -> None:
    """Load the seed into the database configured via DATABASE_URL."""
    settings = load_settings()
    if settings.env is Environment.PROD:
        raise SystemExit("Refusing to seed a production database (ENV=prod).")
    engine = create_async_engine(str(settings.database_url))
    redis = create_redis(str(settings.redis_url))
    try:
        counts = await load(async_sessionmaker(engine), BerlinClock().today())
        # Invalidate cached searches and categories so the API serves the new data at once.
        cache = RedisCache(redis)
        await cache.bump_generation(CATALOG_NAMESPACE)
        await cache.bump_generation(CATEGORIES_NAMESPACE)
    finally:
        await redis.aclose()
        await engine.dispose()
    # Seed data is synthetic; printing counts is safe.
    print("Seed loaded:", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    asyncio.run(main())
