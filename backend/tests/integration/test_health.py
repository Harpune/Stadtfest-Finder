import pytest
from fastapi.testclient import TestClient

from stadtfest.bootstrap.app import create_app
from stadtfest.bootstrap.settings import Settings

pytestmark = pytest.mark.integration


def test_ready_with_real_dependencies(integration_settings: Settings) -> None:
    with TestClient(create_app(integration_settings)) as client:
        response = client.get("/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


def test_ready_reports_unavailable_redis(integration_settings: Settings) -> None:
    broken = integration_settings.model_copy(update={"redis_url": "redis://127.0.0.1:1/0"})
    with TestClient(create_app(broken)) as client:
        response = client.get("/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "ok", "redis": "unavailable"}
