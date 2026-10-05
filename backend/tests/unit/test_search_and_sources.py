"""Web search adapters (recorded answers) and the source check, without network access."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import httpx
import pytest

from stadtfest.adapters.outbound.search.brave import BraveWebSearch
from stadtfest.adapters.outbound.search.searxng import SearxngWebSearch
from stadtfest.adapters.outbound.sources import http as sources
from stadtfest.adapters.outbound.sources.http import HttpSourceChecker
from stadtfest.application.ai_ingestion.ports import WebSearchUnavailableError

FIXTURES = Path(__file__).parents[1] / "fixtures"
BRAVE = json.loads((FIXTURES / "brave" / "web_search_aalen.json").read_text())
SEARXNG = json.loads((FIXTURES / "searxng" / "search_aalen.json").read_text())


async def test_searxng_maps_results_and_sends_only_the_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SEARXNG)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    search = SearxngWebSearch(client, "http://searxng:8080/")
    hits = await search.search("Stadtfest Aalen 2026", 10)

    # Entries without a URL are skipped; failed engines do not matter while there are results.
    assert [hit.url for hit in hits] == [
        "https://www.aalen.de/reichsstaedter-tage",
        "https://www.aalen.de/veranstaltungen",
    ]
    assert hits[0].snippet.startswith("Das große Stadtfest")
    request = seen[0]
    assert str(request.url).startswith("http://searxng:8080/search?")
    assert dict(request.url.params) == {
        "q": "Stadtfest Aalen 2026",
        "format": "json",
        "categories": "general",
        "language": "de-DE",
        "safesearch": "2",
    }
    assert await search.search("Stadtfest Aalen 2026", 1) == hits[:1]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(403),  # JSON format not enabled in settings.yml
        httpx.Response(429),  # limiter of a public instance
        httpx.Response(200, text="<html>"),
        httpx.Response(200, json={"results": [], "unresponsive_engines": [["google", "CAPTCHA"]]}),
    ],
)
async def test_searxng_failures_mean_unavailable(response: httpx.Response) -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response))
    with pytest.raises(WebSearchUnavailableError):
        await SearxngWebSearch(client, "http://searxng:8080").search("x", 5)


async def test_searxng_without_results_is_an_empty_search() -> None:
    body = {"results": [], "unresponsive_engines": []}
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    )
    assert await SearxngWebSearch(client, "http://searxng:8080").search("x", 5) == []


async def test_brave_maps_results_and_sends_only_the_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BRAVE)

    search = BraveWebSearch(httpx.AsyncClient(transport=httpx.MockTransport(handler)), "key")
    hits = await search.search("Stadtfest Aalen 2026", 10)

    assert [hit.url for hit in hits] == [
        "https://www.aalen.de/reichsstaedter-tage",
        "https://www.aalen.de/veranstaltungen",
    ]
    request = seen[0]
    assert request.headers["X-Subscription-Token"] == "key"
    assert request.url.params["q"] == "Stadtfest Aalen 2026"
    assert request.url.params["country"] == "DE"


@pytest.mark.parametrize("status", [401, 429, 500])
async def test_brave_errors_mean_unavailable(status: int) -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(status)))
    with pytest.raises(WebSearchUnavailableError):
        await BraveWebSearch(client, "key").search("x", 5)


def _resolve(monkeypatch: pytest.MonkeyPatch, addresses: dict[str, str]) -> None:
    async def fake_getaddrinfo(host: str, *_args: object, **_kw: object) -> list[object]:
        if host not in addresses:
            raise OSError("unknown host")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addresses[host], 0))]

    class Loop:
        getaddrinfo = staticmethod(fake_getaddrinfo)

    monkeypatch.setattr(sources.asyncio, "get_running_loop", lambda: Loop())


async def test_reachable_pages_pass_and_errors_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    _resolve(monkeypatch, {"www.aalen.de": "93.184.216.34"})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/moved":
            return httpx.Response(301, headers={"location": "/fest"})
        if request.url.path == "/no-head" and request.method == "HEAD":
            return httpx.Response(405)
        return httpx.Response(404 if request.url.path == "/gone" else 200)

    checker = HttpSourceChecker(httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    assert await checker.reachable("https://www.aalen.de/fest")
    assert await checker.reachable("https://www.aalen.de/moved")
    assert await checker.reachable("https://www.aalen.de/no-head")
    assert not await checker.reachable("https://www.aalen.de/gone")
    assert not await checker.reachable("https://unknown.example/x")


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.0.0.5", "192.168.1.2", "169.254.169.254", "::1"]
)
async def test_private_addresses_are_never_requested(
    monkeypatch: pytest.MonkeyPatch, address: str
) -> None:
    _resolve(monkeypatch, {"intern.example": address})
    requested: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        return httpx.Response(200)

    checker = HttpSourceChecker(httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    assert not await checker.reachable("http://intern.example/admin")
    assert requested == []


async def test_redirects_to_private_addresses_are_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _resolve(monkeypatch, {"www.aalen.de": "93.184.216.34", "localhost": "127.0.0.1"})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://localhost:8000/v1/me"})

    checker = HttpSourceChecker(httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    assert not await checker.reachable("https://www.aalen.de/fest")
