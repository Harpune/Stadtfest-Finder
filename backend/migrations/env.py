"""Alembic environment: runs migrations with the async engine from the app settings."""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from stadtfest.bootstrap.settings import load_settings

config = context.config
target_metadata = None  # models are added in R02; autogenerate compares against them


def _database_url() -> str:
    override = config.get_main_option("sqlalchemy.url")
    return override or str(load_settings().database_url)


def run_migrations_offline() -> None:
    """Emit SQL without a database connection (`alembic upgrade --sql`)."""
    context.configure(url=_database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    engine = create_async_engine(_database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
