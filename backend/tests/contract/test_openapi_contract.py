"""Schemathesis: the running app must match api/openapi.yaml (the contract)."""

from collections.abc import Iterator

import pytest
import schemathesis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from schemathesis.python.asgi import ASGIClient

from stadtfest.bootstrap.app import create_app
from stadtfest.bootstrap.settings import Settings
from tests.conftest import REPO_ROOT

pytestmark = pytest.mark.contract

schema = schemathesis.openapi.from_path(REPO_ROOT / "api" / "openapi.yaml")


@pytest.fixture(scope="module")
def app(integration_settings: Settings) -> Iterator[FastAPI]:
    application = create_app(integration_settings)
    with TestClient(application):  # runs the lifespan (container wiring)
        yield application


@schema.parametrize()
def test_api_matches_contract(case: schemathesis.Case, app: FastAPI) -> None:
    with ASGIClient(app) as client:
        case.call_and_validate(session=client, base_url="http://testserver")
