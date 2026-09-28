"""Shared fixtures. Integration and contract tests start real dependencies via Testcontainers."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from stadtfest.bootstrap.settings import Environment, GeocodingProvider, LogFormat, Settings

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
def integration_settings(postgres_url: str, redis_url: str) -> Settings:
    return Settings(
        env=Environment.TEST,
        database_url=postgres_url,
        redis_url=redis_url,
        log_format=LogFormat.CONSOLE,
        geocoding_provider=GeocodingProvider.FAKE,
    )
