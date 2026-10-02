"""Shared fixtures. Integration and contract tests start real dependencies via Testcontainers."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from stadtfest.bootstrap.settings import Environment, GeocodingProvider, LogFormat, Settings
from tests.settings_values import TEST_STORAGE

# Same images as infra/compose.dev.yaml (multi-arch PostGIS, see comment there).
POSTGIS_IMAGE = "imresamu/postgis:17-3.5"
REDIS_IMAGE = "redis:8-alpine"
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer(POSTGIS_IMAGE, driver="asyncpg") as container:
        yield container.get_connection_url()


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    with RedisContainer(REDIS_IMAGE) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"


@pytest.fixture(scope="session")
def migrated_postgres_url(postgres_url: str) -> str:
    """Postgres URL with all Alembic migrations applied (once per session)."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(config, "head")
    return postgres_url


@pytest.fixture(scope="session")
def integration_settings(migrated_postgres_url: str, redis_url: str) -> Settings:
    return Settings(
        env=Environment.TEST,
        database_url=migrated_postgres_url,
        redis_url=redis_url,
        log_format=LogFormat.CONSOLE,
        geocoding_provider=GeocodingProvider.FAKE,
        # Contract tests never reach the storage (clients connect lazily).
        **TEST_STORAGE,  # type: ignore[arg-type]
    )
