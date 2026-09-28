"""Mapping of exceptions to the common error format `{error, message, fields?}`."""

from __future__ import annotations

from collections.abc import Mapping

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from stadtfest.application.shared.errors import (
    InvalidInputError,
    NotFoundError,
    ServiceUnavailableError,
)
from stadtfest.generated.models import Error

logger = structlog.get_logger(__name__)

# Default error codes and German display messages per HTTP status.
_STATUS_ERRORS: dict[int, tuple[str, str]] = {
    400: ("bad_request", "Die Anfrage ist ungültig."),
    401: ("unauthorized", "Bitte melde dich an."),
    403: ("forbidden", "Dafür fehlen dir die Rechte."),
    404: ("not_found", "Nicht mehr verfügbar."),
    405: ("method_not_allowed", "Diese Aktion ist hier nicht erlaubt."),
    409: ("conflict", "Das wurde inzwischen geändert. Bitte neu laden."),
    422: ("validation_failed", "Bitte fülle die markierten Pflichtfelder aus"),
    429: ("rate_limited", "Bitte kurz warten"),
    503: ("service_unavailable", "Der Dienst ist gerade nicht erreichbar. Bitte später erneut."),
}
_INTERNAL_ERROR = ("internal_error", "Da ist etwas schiefgelaufen. Bitte versuche es erneut.")


def error_response(
    status_code: int,
    error: str,
    message: str,
    fields: dict[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build a JSON response in the common error format.

    Args:
        status_code: HTTP status code.
        error: Machine-readable error code.
        message: Human-readable (German) message.
        fields: Optional field-level errors.
        headers: Optional response headers (e.g. `Allow`, `Retry-After`).

    Returns:
        The response.
    """
    body = Error(error=error, message=message, fields=fields)
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
        headers=dict(headers) if headers else None,
    )


async def _handle_http_exception(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101  # registered for this type
    error, message = _STATUS_ERRORS.get(exc.status_code, _INTERNAL_ERROR)
    return error_response(exc.status_code, error, message, headers=exc.headers)


async def _handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101  # registered for this type
    fields: dict[str, str] = {}
    for item in exc.errors():
        location = [
            str(part) for part in item.get("loc", ()) if part not in ("body", "query", "path")
        ]
        fields[".".join(location) or "request"] = str(item.get("type", "invalid"))
    error, message = _STATUS_ERRORS[422]
    return error_response(422, error, message, fields)


async def _handle_not_found(_: Request, exc: Exception) -> JSONResponse:
    return error_response(404, *_STATUS_ERRORS[404])


async def _handle_invalid_input(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, InvalidInputError)  # noqa: S101  # registered for this type
    error, message = _STATUS_ERRORS[422]
    return error_response(422, error, message, exc.fields)


async def _handle_unavailable(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ServiceUnavailableError)  # noqa: S101  # registered for this type
    return error_response(503, exc.code, _STATUS_ERRORS[503][1], headers={"Retry-After": "5"})


async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    # Only the exception type is logged: messages may contain request data.
    logger.error("unhandled_exception", exception_type=type(exc).__name__)
    return error_response(500, *_INTERNAL_ERROR)


def register_error_handlers(app: FastAPI) -> None:
    """Install the exception handlers on the app.

    Args:
        app: The FastAPI application.
    """
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(NotFoundError, _handle_not_found)
    app.add_exception_handler(InvalidInputError, _handle_invalid_input)
    app.add_exception_handler(ServiceUnavailableError, _handle_unavailable)
    app.add_exception_handler(Exception, _handle_unexpected)
