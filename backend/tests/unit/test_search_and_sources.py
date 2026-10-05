"""Web search adapters (recorded answers) and the source check, without network access."""

from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path

import httpx
import pytest

from stadtfest.adapters.outbound.search.brave import BraveWebSearch
from stadtfest.adapters.outbound.search.searxng import SearxngWebSearch
from stadtfest.adapters.outbound.sources import http as sources
from stadtfest.adapters.outbound.sources import pages
from stadtfest.adapters.outbound.sources.http import HttpSourceChecker
from stadtfest.adapters.outbound.sources.pages import HttpPageReader, html_to_text, pdf_to_text
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


async def test_searxng_limits_parallel_requests() -> None:
    """Many parallel queries made the upstream engines block; at most two run at once."""
    running = 0
    peak = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        return httpx.Response(200, json=SEARXNG)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    search = SearxngWebSearch(client, "http://searxng:8080")
    await asyncio.gather(*(search.search(f"q{i}", 5) for i in range(8)))
    assert peak == 2


def test_html_to_text_keeps_visible_text_only() -> None:
    html = (
        "<html><head><title>Stadtfest Aalen</title><style>p{color:red}</style></head>"
        "<body><nav><a>Menü</a></nav><h1>Reichsstädter Tage</h1>"
        "<p>27.&nbsp;September&nbsp;bis 8. Oktober</p><script>track()</script>"
        "<ul><li>Marktplatz</li><li>Marktplatz</li></ul></body></html>"
    )
    assert html_to_text(html) == (
        "Stadtfest Aalen\nReichsstädter Tage\n27. September bis 8. Oktober\nMarktplatz"
    )


async def test_page_reader_reads_html_and_refuses_other_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _resolve(monkeypatch, {"www.aalen.de": "93.184.216.34"})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/fest":
            html = "<html><body><h1>Stadtfest</h1><p>17. Oktober</p></body></html>"
            return httpx.Response(200, html=html)
        if request.url.path == "/plan.pdf":
            return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})
        if request.url.path == "/bild.png":
            return httpx.Response(200, content=b"png", headers={"content-type": "image/png"})
        return httpx.Response(404)

    reader = HttpPageReader(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert await reader.read("https://www.aalen.de/fest", 100) == "Stadtfest\n17. Oktober"
    assert await reader.read("https://www.aalen.de/fest", 9) == "Stadtfest"
    assert await reader.read("https://www.aalen.de/plan.pdf", 100) is None  # broken PDF
    assert await reader.read("https://www.aalen.de/bild.png", 100) is None
    assert await reader.read("https://www.aalen.de/weg", 100) is None


def _pdf(*lines: str) -> bytes:
    """A minimal one-page PDF with one text line per argument (ASCII only)."""
    content = "BT /F1 12 Tf 72 720 Td " + " ".join(f"({line}) Tj 0 -14 Td" for line in lines)
    content += " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out


def test_pdf_to_text_reads_lines_and_rejects_garbage() -> None:
    pdf = _pdf("Veranstaltungskalender 2027", "12. Juni   Weinfest  Kirchberg")
    assert pdf_to_text(pdf, 1000) == "Veranstaltungskalender 2027\n12. Juni Weinfest Kirchberg"
    assert pdf_to_text(pdf, 10) == "Veranstalt"
    assert pdf_to_text(b"%PDF-1.4 kaputt", 100) is None
    assert pdf_to_text(_pdf(), 100) is None


async def test_page_reader_reads_pdfs_up_to_a_size_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _resolve(monkeypatch, {"www.kirchberg.de": "93.184.216.34"})
    monkeypatch.setattr(pages, "MAX_PDF_BYTES", 2_000)
    pdf = _pdf("Kirmes Kirchberg", "3. bis 5. September")

    def handler(request: httpx.Request) -> httpx.Response:
        body = pdf if request.url.path == "/kalender.pdf" else pdf + b" " * 2_000
        return httpx.Response(200, content=body, headers={"content-type": "application/pdf"})

    reader = HttpPageReader(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert await reader.read("https://www.kirchberg.de/kalender.pdf", 100) == (
        "Kirmes Kirchberg\n3. bis 5. September"
    )
    # A cut PDF cannot be parsed, so larger files are skipped.
    assert await reader.read("https://www.kirchberg.de/broschuere.pdf", 100) is None


async def test_page_reader_blocks_redirects_to_internal_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _resolve(monkeypatch, {"www.aalen.de": "93.184.216.34", "intern": "10.0.0.5"})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://intern/secret"})

    reader = HttpPageReader(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert await reader.read("https://www.aalen.de/fest", 100) is None
