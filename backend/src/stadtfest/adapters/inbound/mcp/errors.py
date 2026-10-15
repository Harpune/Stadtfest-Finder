"""Mapping of application errors to understandable tool errors (German / English)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastmcp.exceptions import ToolError

from stadtfest.application.shared.errors import (
    ApplicationError,
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
    ServiceUnavailableError,
    TooManyRequestsError,
)

_CODE_MESSAGES: dict[str, str] = {
    "postal_code_unknown": "Diese Postleitzahl kennen wir nicht. / Unknown German postal code.",
    "search_running": (
        "Für dich läuft schon eine KI-Suche. Warte, bis sie fertig ist. "
        "/ An AI search of yours is already running; wait until it has finished."
    ),
    "daily_limit": (
        "Du hast heute schon die maximale Anzahl an KI-Suchen gestartet. "
        "/ Daily limit of AI searches reached."
    ),
}
_NOT_FOUND = (
    "Dieses Fest gibt es nicht oder es ist nicht veröffentlicht. "
    "/ Event not found or not published."
)
_FORBIDDEN = "Dafür fehlt dir die Rolle Moderator. / Requires the moderator role."
_INVALID = "Ungültige Eingabe / Invalid input"
_UNAVAILABLE = (
    "Der Dienst ist gerade nicht erreichbar. Bitte später erneut. "
    "/ Service temporarily unavailable, try again later."
)


def _message(error: ApplicationError) -> str:
    if error.code in _CODE_MESSAGES:
        message = _CODE_MESSAGES[error.code]
        job_id = (error.fields or {}).get("jobId") if isinstance(error, ConflictError) else None
        return f"{message} (jobId {job_id})" if job_id else message
    match error:
        case NotFoundError():
            return _NOT_FOUND
        case ForbiddenError():
            return _FORBIDDEN
        case InvalidInputError():
            return f"{_INVALID}: {', '.join(sorted(error.fields))}"
        case ServiceUnavailableError():
            return _UNAVAILABLE
        case TooManyRequestsError():
            return "Zu viele Anfragen. / Too many requests."
        case _:
            return "Die Anfrage ist nicht möglich. / The request is not possible."


@contextmanager
def tool_errors() -> Iterator[None]:
    """Turn expected application errors into `ToolError`s with a readable message.

    Unexpected exceptions propagate; FastMCP masks their details (`mask_error_details`).
    """
    try:
        yield
    except ApplicationError as error:
        raise ToolError(_message(error)) from None
