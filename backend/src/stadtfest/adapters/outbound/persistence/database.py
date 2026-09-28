"""Async SQLAlchemy engine and a readiness probe for PostgreSQL."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    """Create the process-wide async engine.

    Args:
        database_url: SQLAlchemy URL using the asyncpg driver.

    Returns:
        The engine; dispose it on shutdown.
    """
    return create_async_engine(database_url, pool_pre_ping=True)


class DatabaseProbe:
    """Readiness probe that runs `SELECT 1` against the database."""

    name = "database"

    def __init__(self, engine: AsyncEngine) -> None:
        """Create the probe.

        Args:
            engine: Engine to check.
        """
        self._engine = engine

    async def is_available(self) -> bool:
        """Return True if the database answers."""
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
