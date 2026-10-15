"""OAuth 2.1 resource server for the MCP endpoint (R15-US2).

The server accepts guests: `search_events` and `get_event` are public, like the REST catalog.
A present bearer token is validated on every request with the same `Authenticate` use case as
the REST API, an invalid one is rejected with `401`. Tools that need a login answer guests with
`401` and a pointer to the Protected Resource Metadata (RFC 9728), so MCP clients start the
OAuth flow and retry. Roles (`moderator`) are checked in the use cases, not here.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from fastmcp.server.dependencies import get_http_request
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from stadtfest.adapters.inbound.auth.bearer import Authenticator, principal_from_header
from stadtfest.adapters.inbound.mcp.dependencies import McpConfig
from stadtfest.application.identity.ports import InvalidTokenError
from stadtfest.application.shared.errors import ServiceUnavailableError
from stadtfest.domain.identity.principal import Principal

PRINCIPAL_STATE_KEY = "stadtfest_principal"
# JSON-RPC requests of the tools are small; larger bodies are rejected before parsing.
MAX_BODY_BYTES = 64 * 1024


def current_principal() -> Principal | None:
    """The caller of the current tool call, or None for guests."""
    try:
        request = get_http_request()
    except RuntimeError:  # no HTTP request, e.g. in-memory transport
        return None
    principal = request.scope.get("state", {}).get(PRINCIPAL_STATE_KEY)
    return principal if isinstance(principal, Principal) else None


def protected_resource_metadata(config: McpConfig) -> dict[str, object]:
    """Protected Resource Metadata (RFC 9728) naming the IdP as authorization server."""
    return {
        "resource": config.resource,
        "authorization_servers": [config.authorization_server],
        "scopes_supported": list(config.scopes),
        "bearer_methods_supported": ["header"],
        "resource_name": "Stadtfest-Finder",
    }


class OptionalBearerAuth:
    """ASGI middleware: validate a present token, admit guests, challenge login-only tools.

    The principal is stored in the ASGI scope state, where the tools read it per request.
    Tokens, headers and request bodies are never logged.
    """

    def __init__(
        self,
        app: ASGIApp,
        authenticate: Authenticator,
        config: McpConfig,
        login_tools: Iterable[str],
    ) -> None:
        """Wrap the MCP app.

        Args:
            app: The wrapped Starlette app.
            authenticate: The `Authenticate` use case.
            config: Server addresses for the `WWW-Authenticate` challenge.
            login_tools: Tools that need a signed-in caller.
        """
        self._app = app
        self._authenticate = authenticate
        self._config = config
        self._login_tools = frozenset(login_tools)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one ASGI call."""
        if scope["type"] != "http" or scope["path"].rstrip("/") != self._config.path:
            await self._app(scope, receive, send)
            return
        try:
            principal = await principal_from_header(
                Headers(scope=scope).get("authorization"), self._authenticate
            )
        except InvalidTokenError:
            await self._challenge(scope, receive, send, error="invalid_token")
            return
        except ServiceUnavailableError:
            response = JSONResponse({"error": "auth_unavailable"}, 503, {"Retry-After": "5"})
            await response(scope, receive, send)
            return
        if principal is None and scope["method"] == "POST":
            body = await _read_body(receive)
            if body is None:
                await JSONResponse({"error": "payload_too_large"}, 413)(scope, receive, send)
                return
            if self._calls_login_tool(body):
                await self._challenge(scope, receive, send)
                return
            receive = _replay(body, receive)
        scope.setdefault("state", {})[PRINCIPAL_STATE_KEY] = principal
        await self._app(scope, receive, send)

    def _calls_login_tool(self, body: bytes) -> bool:
        try:
            payload = json.loads(body)
        except ValueError:
            return False  # the MCP transport answers with a parse error
        messages = payload if isinstance(payload, list) else [payload]
        for message in messages:
            if not isinstance(message, dict) or message.get("method") != "tools/call":
                continue
            params = message.get("params")
            if isinstance(params, dict) and params.get("name") in self._login_tools:
                return True
        return False

    async def _challenge(
        self, scope: Scope, receive: Receive, send: Send, error: str | None = None
    ) -> None:
        parts = [f'error="{error}"'] if error else []
        parts += [
            f'resource_metadata="{self._config.resource_metadata_url}"',
            f'scope="{" ".join(self._config.scopes)}"',
        ]
        body = {
            "error": error or "unauthorized",
            "message": "Anmeldung erforderlich. / Sign-in required (OAuth).",
        }
        response = JSONResponse(body, 401, {"WWW-Authenticate": "Bearer " + ", ".join(parts)})
        await response(scope, receive, send)


async def _read_body(receive: Receive) -> bytes | None:
    """Read the whole request body, or None if it exceeds `MAX_BODY_BYTES`."""
    chunks: list[bytes] = []
    size = 0
    while True:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunk: bytes = message.get("body", b"")
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            return None
        chunks.append(chunk)
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _replay(body: bytes, receive: Receive) -> Receive:
    """Return a `receive` that yields the buffered body once, then the original stream."""
    sent = False

    async def replay() -> Message:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await receive()

    return replay
