"""Structured logging setup with a privacy filter.

CLAUDE.md forbids logging personal data (emails, names, tokens, IPs, free text, user
coordinates). The `scrub_personal_data` processor enforces this for every log entry,
including entries from third-party libraries routed through the standard library.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from stadtfest.bootstrap.settings import LogFormat, Settings

REDACTED = "[redacted]"

# Keys whose values may contain personal data or secrets. Matched case-insensitively.
_DENYLISTED_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "password",
        "secret",
        "email",
        "first_name",
        "last_name",
        "firstname",
        "lastname",
        "ip",
        "client_ip",
        "client",
        "peer",
        "remote_addr",
        "x-forwarded-for",
        "lat",
        "lon",
        "latitude",
        "longitude",
        "q",
        "query",
        "query_string",
        "message_text",
    }
)
_BEARER_PATTERN = re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]+")
_QUERY_PATTERN = re.compile(r"\?[^\s\"']*")
_URL_KEYS = frozenset({"path", "url", "target"})


def _scrub_value(key: str, value: Any) -> Any:  # noqa: ANN401  # log values are arbitrary
    if key.lower() in _DENYLISTED_KEYS:
        return REDACTED
    if isinstance(value, str):
        value = _BEARER_PATTERN.sub("Bearer " + REDACTED, value)
        if key.lower() in _URL_KEYS:
            value = _QUERY_PATTERN.sub("", value)
        return value
    if isinstance(value, MutableMapping):
        return {k: _scrub_value(str(k), v) for k, v in value.items()}
    return value


def scrub_personal_data(
    _logger: Any,  # noqa: ANN401  # structlog processor signature
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Redact denylisted keys, bearer tokens and URL query strings from a log entry.

    Args:
        _logger: The wrapped logger (unused).
        _method_name: The log method name (unused).
        event_dict: The log entry.

    Returns:
        The scrubbed log entry.
    """
    for key in list(event_dict.keys()):
        if key.startswith("_"):
            continue  # structlog internals such as `_record`
        event_dict[key] = _scrub_value(key, event_dict[key])
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Configure structlog and route standard-library logging through it.

    Args:
        settings: Application settings (log level and format).
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.ExtraAdder(),
        scrub_personal_data,
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_format is LogFormat.JSON
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
        )
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(settings.log_level)

    # Uvicorn's access log contains client IPs and query strings; we log requests ourselves.
    logging.getLogger("uvicorn.access").disabled = True
    # httpx logs every outgoing request with its full URL at INFO: search text and
    # coordinates (Nominatim) and IdP user IDs (account deletion) would end up in the log.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
