"""FastMCP server and its Starlette app: Streamable HTTP under `/mcp`, health, OAuth metadata."""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

import mcp_types as mt
import structlog
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from starlette.middleware import Middleware as AsgiMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from stadtfest.adapters.inbound.mcp.auth import (
    OptionalBearerAuth,
    current_principal,
    protected_resource_metadata,
)
from stadtfest.adapters.inbound.mcp.dependencies import McpConfig, McpDependencies
from stadtfest.adapters.inbound.mcp.tools import LOGIN_TOOLS, register_tools
from stadtfest.adapters.inbound.rest.middleware import RequestContextMiddleware

logger = structlog.get_logger("stadtfest.mcp")

RATE_LIMIT_CALLS = 60
RATE_LIMIT_WINDOW_SECONDS = 60
INSTRUCTIONS = """\
Stadtfest-Finder: Feste in Deutschland (Stadtfeste, Volksfeste, Kirmes, Weihnachtsmärkte, \
Märkte). Suche per Postleitzahl, Details per ID. Moderatoren können eine KI-Suche starten.
Festivals and fairs in Germany: search by postal code, details by ID. Moderators can start an \
AI search for new events (drafts, reviewed before publishing)."""

Lifespan = Callable[[FastMCP], AbstractAsyncContextManager[None]]


class ToolCallGuard(Middleware):
    """Rate limit per token or client IP (R15-US3) and one log line per tool call.

    The log line holds the tool name, the outcome and the duration: never the arguments
    (postal codes), the user ID or the token (R15-US4).
    """

    def __init__(self, deps: McpDependencies) -> None:
        """Create the guard on the shared rate limiter (Redis, keys are hashed)."""
        self._deps = deps

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        """Count the call against the limit, then run the tool."""
        tool = context.message.name
        if not await self._deps.rate_limiter.hit(
            _client_key(), RATE_LIMIT_CALLS, RATE_LIMIT_WINDOW_SECONDS
        ):
            logger.info("mcp_tool_call", tool=tool, outcome="rate_limited")
            raise ToolError(
                "Zu viele Aufrufe. Bitte warte eine Minute. "
                "/ Rate limit of 60 calls per minute exceeded."
            )
        started = time.perf_counter()
        outcome = "error"
        try:
            result = await call_next(context)
            outcome = "ok"
            return result
        except ToolError:
            outcome = "tool_error"
            raise
        finally:
            logger.info(
                "mcp_tool_call",
                tool=tool,
                outcome=outcome,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )


def _client_key() -> str:
    principal = current_principal()
    if principal is not None:
        return f"mcp:sub:{principal.subject}"
    try:
        client = get_http_request().client
    except RuntimeError:
        client = None
    return f"mcp:ip:{client.host if client else 'unknown'}"


def create_mcp_server(
    deps: McpDependencies, config: McpConfig, lifespan: Lifespan | None = None
) -> FastMCP:
    """Create the FastMCP server with its tools, health and metadata routes.

    Args:
        deps: Use cases from the composition root (shared with REST and worker).
        config: Public addresses of the server.
        lifespan: Optional server lifespan, e.g. to close the container.

    Returns:
        The server; serve it with `create_mcp_app`.
    """
    server = FastMCP(
        name="Stadtfest-Finder",
        instructions=INSTRUCTIONS,
        version="0.1.0",
        mask_error_details=True,
        middleware=[ToolCallGuard(deps)],
        lifespan=lifespan,
    )
    register_tools(server, deps, config)

    @server.custom_route("/health/live", methods=["GET"])
    async def live(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @server.custom_route("/health/ready", methods=["GET"])
    async def ready(_: Request) -> JSONResponse:
        readiness = await deps.check_readiness()
        checks = {name: "ok" if ok else "unavailable" for name, ok in readiness.checks.items()}
        status = "ok" if readiness.ready else "unavailable"
        return JSONResponse(
            {"status": status, "checks": checks}, status_code=200 if readiness.ready else 503
        )

    async def metadata(_: Request) -> JSONResponse:
        return JSONResponse(protected_resource_metadata(config))

    # RFC 9728 path-suffixed form, plus the root form some clients try first.
    for path in (config.resource_metadata_path, "/.well-known/oauth-protected-resource"):
        server.custom_route(path, methods=["GET"])(metadata)
    return server


def asgi_middleware(deps: McpDependencies, config: McpConfig) -> list[AsgiMiddleware]:
    """HTTP middleware of the MCP app: request logging, then optional bearer auth."""
    return [
        AsgiMiddleware(RequestContextMiddleware),
        AsgiMiddleware(
            OptionalBearerAuth,
            authenticate=deps.authenticate,
            config=config,
            login_tools=LOGIN_TOOLS,
        ),
    ]


def http_app_options(deps: McpDependencies, config: McpConfig) -> dict[str, object]:
    """Keyword arguments for `FastMCP.http_app` (also used by the tests' in-process server).

    Stateless JSON mode: every request carries its own token, no session state is kept.
    """
    return {
        "path": config.path,
        "middleware": asgi_middleware(deps, config),
        "stateless_http": True,
        "json_response": True,
    }
