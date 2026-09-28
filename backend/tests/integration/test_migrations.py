import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_upgrade_head_enables_extensions(postgres_url: str) -> None:
    extensions = _upgrade_and_list_extensions(postgres_url)
    assert {"postgis", "pg_trgm", "unaccent"} <= extensions


def _upgrade_and_list_extensions(postgres_url: str) -> set[str]:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", postgres_url)

    command.upgrade(config, "head")

    return asyncio.run(_list_extensions(postgres_url))


async def _list_extensions(postgres_url: str) -> set[str]:
    engine = create_async_engine(postgres_url)
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT extname FROM pg_extension"))
        extensions = set(result.scalars())
    await engine.dispose()
    return extensions
