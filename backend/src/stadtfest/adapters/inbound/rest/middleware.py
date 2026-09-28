"""ASGI middleware: request IDs and privacy-preserving request logging."""

from __future__ import annotations

import re
import time
import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger("stadtfest.request")

REQUEST_ID_HEADER = "x-request-id"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


class RequestContextMiddleware:
    """Assign a request ID, expose it as response header and log one line per request.

    The log line contains method, path (without query string), status and duration.
    Client IPs, headers and query parameters are never logged.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap an ASGI app.

        Args:
            app: The wrapped application.
        """
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one ASGI call."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = self._incoming_request_id(scope) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.encode(), request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self._app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request",
                method=scope["method"],
                path=scope["path"],
                status=status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            structlog.contextvars.clear_contextvars()

    @staticmethod
    def _incoming_request_id(scope: Scope) -> str | None:
        for name, value in scope.get("headers", []):
            if name.decode().lower() == REQUEST_ID_HEADER:
                candidate = value.decode()
                return candidate if _VALID_REQUEST_ID.match(candidate) else None
        return None
