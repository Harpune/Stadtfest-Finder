"""Smoke test after a deployment (R16): `python -m stadtfest.bootstrap.smoke`.

Checks the public entry points of a running stack without a token and without side effects:
API health, `GET /v1/categories`, `GET /v1/events` and the MCP tool `search_events`.
Exits with 0 if every check passed, 1 otherwise. Prints only check names, status codes and
durations (no response bodies), so the output can go into CI logs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

import httpx

# Viewport covering Germany, so the check does not depend on the content of one region.
GERMANY_BBOX = "5.87,47.27,15.04,55.06"
DEFAULT_ZIP_CODE = "73430"
_MCP_HEADERS = {"Accept": "application/json, text/event-stream"}
_PROTOCOL_VERSION = "2025-06-18"


class SmokeError(Exception):
    """A check failed; the message names the reason without response content."""


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one check."""

    name: str
    ok: bool
    detail: str
    duration_ms: float


Check = Callable[[httpx.AsyncClient], Awaitable[str]]


def _expect_status(response: httpx.Response, status: int = 200) -> None:
    if response.status_code != status:
        raise SmokeError(f"HTTP {response.status_code}, expected {status}")


async def check_api_live(client: httpx.AsyncClient) -> str:
    """`GET /v1/health/live` answers 200."""
    response = await client.get("/v1/health/live")
    _expect_status(response)
    return "HTTP 200"


async def check_api_ready(client: httpx.AsyncClient) -> str:
    """`GET /v1/health/ready` answers 200 (database, Redis and other dependencies reachable)."""
    response = await client.get("/v1/health/ready")
    _expect_status(response)
    return "HTTP 200"


async def check_categories(client: httpx.AsyncClient) -> str:
    """`GET /v1/categories` returns a list (empty right after the first installation)."""
    response = await client.get("/v1/categories")
    _expect_status(response)
    categories = response.json()
    if not isinstance(categories, list):
        raise SmokeError("unexpected response shape")
    return f"{len(categories)} categories"


async def check_events(client: httpx.AsyncClient) -> str:
    """`GET /v1/events` answers 200 with a page of events (may be empty)."""
    response = await client.get("/v1/events", params={"bbox": GERMANY_BBOX})
    _expect_status(response)
    page = response.json()
    if not isinstance(page, dict) or not isinstance(page.get("items"), list):
        raise SmokeError("unexpected response shape")
    return f"{len(page['items'])} events"


def _rpc_result(response: httpx.Response) -> dict[str, object]:
    _expect_status(response)
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        data = [line[5:] for line in response.text.splitlines() if line.startswith("data:")]
        if not data:
            raise SmokeError("empty event stream")
        message = json.loads(data[-1])
    else:
        message = response.json()
    if "error" in message:
        raise SmokeError(f"JSON-RPC error {message['error'].get('code')}")
    result: dict[str, object] = message["result"]
    return result


def search_events_check(zip_code: str) -> Check:
    """MCP: `initialize`, then `tools/call search_events` without a token."""

    async def check_mcp_search_events(client: httpx.AsyncClient) -> str:
        initialized = _rpc_result(
            await client.post(
                "/mcp",
                headers=_MCP_HEADERS,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": _PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": "stadtfest-smoke", "version": "1"},
                    },
                },
            )
        )
        headers = {
            **_MCP_HEADERS,
            "MCP-Protocol-Version": str(initialized.get("protocolVersion", _PROTOCOL_VERSION)),
        }
        await client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        result = _rpc_result(
            await client.post(
                "/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "search_events",
                        "arguments": {"zip_code": zip_code, "radius_km": 50},
                    },
                },
            )
        )
        if result.get("isError"):
            raise SmokeError("search_events returned a tool error")
        structured = result.get("structuredContent")
        if not isinstance(structured, dict) or not isinstance(structured.get("events"), list):
            raise SmokeError("search_events returned no event list")
        return f"{len(structured['events'])} events"

    return check_mcp_search_events


async def _run(name: str, check: Check, client: httpx.AsyncClient) -> CheckResult:
    started = time.perf_counter()
    try:
        detail, ok = await check(client), True
    except SmokeError as error:
        detail, ok = str(error), False
    except (httpx.HTTPError, ValueError, KeyError) as error:
        detail, ok = type(error).__name__, False
    return CheckResult(name, ok, detail, round((time.perf_counter() - started) * 1000, 1))


async def run_smoke_tests(
    api: httpx.AsyncClient, mcp: httpx.AsyncClient, zip_code: str = DEFAULT_ZIP_CODE
) -> list[CheckResult]:
    """Run all checks; API and MCP clients carry their base URLs.

    Args:
        api: Client for the REST API.
        mcp: Client for the MCP server.
        zip_code: Postal code for `search_events`.

    Returns:
        One result per check, in order.
    """
    checks: list[tuple[str, Check, httpx.AsyncClient]] = [
        ("api health live", check_api_live, api),
        ("api health ready", check_api_ready, api),
        ("GET /v1/categories", check_categories, api),
        ("GET /v1/events", check_events, api),
        ("MCP search_events", search_events_check(zip_code), mcp),
    ]
    return [await _run(name, check, client) for name, check, client in checks]


async def _main(args: argparse.Namespace) -> int:
    timeout = httpx.Timeout(args.timeout)
    async with (
        httpx.AsyncClient(base_url=args.api_url, timeout=timeout) as api,
        httpx.AsyncClient(base_url=args.mcp_url, timeout=timeout) as mcp,
    ):
        results = await run_smoke_tests(api, mcp, args.zip_code)
    for result in results:
        mark = "ok  " if result.ok else "FAIL"
        print(f"{mark} {result.name:<22} {result.detail} ({result.duration_ms} ms)")
    return 0 if all(result.ok for result in results) else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and run the smoke tests.

    Args:
        argv: Arguments without the program name (default: `sys.argv[1:]`).

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api-url", required=True, help="e.g. https://api.example.eu")
    parser.add_argument("--mcp-url", required=True, help="e.g. https://mcp.example.eu")
    parser.add_argument("--zip-code", default=DEFAULT_ZIP_CODE)
    parser.add_argument("--timeout", type=float, default=10.0, help="seconds per request")
    return asyncio.run(_main(parser.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
