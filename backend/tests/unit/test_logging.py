import json
import logging

import pytest
import structlog

from stadtfest.bootstrap.logging import REDACTED, configure_logging, scrub_personal_data
from stadtfest.bootstrap.settings import LogFormat, Settings


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
        log_format=LogFormat.JSON,
    )


@pytest.mark.parametrize(
    "key", ["lat", "lon", "q", "email", "authorization", "token", "client_ip", "first_name"]
)
def test_denylisted_keys_are_redacted(key: str) -> None:
    result = scrub_personal_data(None, "info", {"event": "x", key: "sensitive"})
    assert result[key] == REDACTED


def test_query_strings_are_removed_from_paths() -> None:
    result = scrub_personal_data(None, "info", {"path": "/v1/events?lat=48.8&lon=10.1&q=aalen"})
    assert result["path"] == "/v1/events"


def test_bearer_tokens_are_redacted_everywhere() -> None:
    result = scrub_personal_data(None, "info", {"event": "failed with Bearer eyJhbGciOi.abc.def"})
    assert "eyJ" not in result["event"]


def test_nested_mappings_are_scrubbed() -> None:
    result = scrub_personal_data(None, "info", {"event": "x", "headers": {"Authorization": "a"}})
    assert result["headers"] == {"Authorization": REDACTED}


def test_stdlib_log_output_contains_no_personal_data(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(_settings())

    structlog.get_logger("test").info(
        "request", path="/v1/events?lat=48.83&lon=10.09", lat=48.83, email="a@b.test"
    )
    logging.getLogger("thirdparty").info("call", extra={"q": "Aalen", "token": "abc123"})

    output = capsys.readouterr().out
    for fragment in ("48.83", "10.09", "a@b.test", "Aalen", "abc123"):
        assert fragment not in output
    lines = [json.loads(line) for line in output.strip().splitlines()]
    assert lines[0]["path"] == "/v1/events"
