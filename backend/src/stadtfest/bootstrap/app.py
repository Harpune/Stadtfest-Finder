"""FastAPI application factory (entry point for uvicorn)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from stadtfest.adapters.inbound.rest import categories, events, geocoding, health
from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.adapters.inbound.rest.middleware import RequestContextMiddleware
from stadtfest.bootstrap.container import Container
from stadtfest.bootstrap.logging import configure_logging
from stadtfest.bootstrap.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the REST API application.

    Run with `uvicorn stadtfest.bootstrap.app:create_app --factory`.

    Args:
        settings: Settings to use; loaded from the environment if omitted.

    Returns:
        The configured application.
    """
    settings = settings or get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = Container.build(settings)
        app.state.container = container
        app.state.check_readiness = container.check_readiness
        try:
            yield
        finally:
            await container.aclose()

    app = FastAPI(
        title="Stadtfest-Finder API",
        version="0.1.0",
        lifespan=lifespan,
        # The contract lives in api/openapi.yaml; no generated docs in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(categories.router)
    app.include_router(events.router)
    app.include_router(geocoding.router)
    return app
