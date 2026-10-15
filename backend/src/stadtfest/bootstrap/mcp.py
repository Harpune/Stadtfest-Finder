"""MCP server entry point: `python -m stadtfest.bootstrap.mcp` (R15, flow D)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastmcp import FastMCP
from starlette.applications import Starlette

from stadtfest.adapters.inbound.mcp.dependencies import McpConfig
from stadtfest.adapters.inbound.mcp.server import create_mcp_server, http_app_options
from stadtfest.bootstrap.container import Container
from stadtfest.bootstrap.logging import configure_logging
from stadtfest.bootstrap.settings import Settings, get_settings


def mcp_config(settings: Settings) -> McpConfig:
    """Public addresses of the MCP server from the settings."""
    return McpConfig(
        public_url=str(settings.mcp_public_url).rstrip("/"),
        # Exactly the issuer the tokens are validated against (see `Container.build`).
        authorization_server=str(settings.auth_issuer).rstrip("/"),
        link_base_url=str(settings.deep_link_base_url).rstrip("/"),
        scopes=tuple(settings.mcp_oauth_scopes.split()),
    )


def create_mcp_app(settings: Settings | None = None) -> Starlette:
    """Create the MCP server's ASGI app with the same composition root as the REST API.

    Args:
        settings: Settings to use; loaded from the environment if omitted.

    Returns:
        The Starlette app serving `/mcp`, `/health/*` and the OAuth metadata.
    """
    settings = settings or get_settings()
    configure_logging(settings)
    # FastMCP logs tool calls and protocol details; our guard writes a privacy-safe line.
    for name in ("fastmcp", "mcp"):
        logging.getLogger(name).setLevel(logging.WARNING)
    container = Container.build(settings)
    config = mcp_config(settings)

    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await container.aclose()

    server = create_mcp_server(container, config, lifespan)
    return server.http_app(**http_app_options(container, config))  # type: ignore[arg-type]


def main() -> None:
    """Serve the MCP server with uvicorn until interrupted."""
    settings = get_settings()
    uvicorn.run(
        create_mcp_app(settings),
        host=settings.mcp_host,
        port=settings.mcp_port,
        proxy_headers=True,
        access_log=False,
    )


if __name__ == "__main__":
    main()
