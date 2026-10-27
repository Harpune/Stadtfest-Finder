"""Reading result pages for the LLM (R10b-US5) with the SSRF protection of the source check.

Only HTML, plain text and PDF are read. HTML and text are cut at `MAX_BYTES`; scripts,
styles and navigation are dropped. Links of an HTML page outside navigation are kept (at
most `MAX_LINKS`, R10c) so the model can name an event's own website without guessing it.
PDFs (town event calendars are often PDFs) are read up to `MAX_PDF_BYTES` and
`MAX_PDF_PAGES` pages, larger ones are skipped because a cut PDF cannot be parsed. The
visible text is shortened to the requested length. No cookies, redirects are followed
manually so every host is checked.
"""

from __future__ import annotations

import asyncio
import re
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from pypdf import PasswordType, PdfReader

from stadtfest.adapters.outbound.sources.http import is_public_host
from stadtfest.application.ai_ingestion.ports import PageContent, PageLink

MAX_BYTES = 1_500_000
MAX_PDF_BYTES = 8_000_000
MAX_PDF_PAGES = 40
MAX_REDIRECTS = 3
MAX_LINKS = 40
MAX_LINK_TEXT = 80
_TEXT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
_PDF_TYPE = "application/pdf"
_SKIPPED = frozenset({"script", "style", "noscript", "svg", "template", "iframe", "nav"})
_BLOCKS = frozenset(
    {
        "p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article", "header",
        "footer", "main", "aside", "h1", "h2", "h3", "h4", "h5", "h6", "dt", "dd", "title",
    }
)  # fmt: skip


class _TextExtractor(HTMLParser):
    """Visible text with line breaks at block elements, and the visible links."""

    def __init__(self, base_url: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self._skip_depth = 0
        self._parts: list[str] = []
        self._href: str | None = None
        self._link_text: list[str] = []
        self.links: list[PageLink] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED:
            self._skip_depth += 1
        elif tag in _BLOCKS:
            self._parts.append("\n")
        if tag == "a" and not self._skip_depth and self._base_url:
            self._href = dict(attrs).get("href")
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED and self._skip_depth:
            self._skip_depth -= 1
        elif tag in _BLOCKS:
            self._parts.append("\n")
        if tag == "a" and self._href is not None:
            self._add_link(self._href, " ".join("".join(self._link_text).split()))
            self._href = None

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)
            if self._href is not None:
                self._link_text.append(data)

    def _add_link(self, href: str, text: str) -> None:
        if len(self.links) >= MAX_LINKS or len(text) < 3:
            return
        parts = urlsplit(urljoin(self._base_url, href.strip()))
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            return
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
        if url == self._base_url or any(link.url == url for link in self.links):
            return
        self.links.append(PageLink(url, text[:MAX_LINK_TEXT]))

    def text(self) -> str:
        lines = (re.sub(r"\s+", " ", line).strip() for line in "".join(self._parts).split("\n"))
        result: list[str] = []
        for line in lines:
            if line and (not result or result[-1] != line):
                result.append(line)
        return "\n".join(result)


def html_to_text(html: str) -> str:
    """Visible text of an HTML document, one block per line."""
    return html_to_page(html, "", 0).text


def html_to_page(html: str, base_url: str, max_chars: int) -> PageContent:
    """Visible text (cut at `max_chars`, 0 = uncut) and absolute links outside navigation."""
    parser = _TextExtractor(base_url)
    parser.feed(html)
    parser.close()
    text = parser.text()
    return PageContent(text[:max_chars] if max_chars else text, tuple(parser.links))


def pdf_to_text(data: bytes, max_chars: int) -> str | None:
    """Text of a PDF, page by page until `max_chars` or `MAX_PDF_PAGES`; None if unreadable.

    Encrypted PDFs are read only if they open with an empty password (permission locks).
    """
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted and reader.decrypt("") == PasswordType.NOT_DECRYPTED:
            return None
        lines: list[str] = []
        size = 0
        for index in range(min(len(reader.pages), MAX_PDF_PAGES)):
            for line in reader.pages[index].extract_text().splitlines():
                line = re.sub(r"\s+", " ", line).strip()
                if line:
                    lines.append(line)
                    size += len(line) + 1
            if size >= max_chars:
                break
    # The PDF comes from an arbitrary web page and pypdf raises many different exception
    # types for broken files; any of them only means "cannot be read".
    except Exception:  # noqa: BLE001
        return None
    return "\n".join(lines)[:max_chars] or None


class HttpPageReader:
    """Implements `PageReader` with GET, public hosts only, size and type limits."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Create the reader.

        Args:
            client: HTTP client without cookies that does not follow redirects itself.
        """
        self._client = client

    async def read(self, url: str, max_chars: int) -> PageContent | None:
        """Visible text (at most `max_chars`) and links of the page; None if unreadable."""
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            parts = urlsplit(current)
            if parts.scheme not in {"http", "https"} or not parts.hostname:
                return None
            if not await is_public_host(parts.hostname):
                return None
            try:
                async with self._client.stream("GET", current) as response:
                    if response.is_redirect and "location" in response.headers:
                        current = str(response.url.join(response.headers["location"]))
                        continue
                    if response.status_code >= 400:
                        return None
                    content_type = response.headers.get("content-type", "").lower()
                    if content_type.startswith(_PDF_TYPE):
                        pdf = await _limited_body(response, MAX_PDF_BYTES + 1)
                    elif content_type.startswith(_TEXT_TYPES):
                        pdf = None
                        body = await _limited_body(response, MAX_BYTES)
                        text = body.decode(response.encoding or "utf-8", errors="replace")
                    else:
                        return None
            except httpx.HTTPError:
                return None
            if pdf is not None:
                if len(pdf) > MAX_PDF_BYTES:
                    return None
                # Parsing is CPU-bound; keep the event loop free for the other requests.
                pdf_text = await asyncio.to_thread(pdf_to_text, pdf, max_chars)
                return PageContent(pdf_text) if pdf_text else None
            if content_type.startswith("text/plain"):
                return PageContent(text[:max_chars]) if text[:max_chars] else None
            page = html_to_page(text, current, max_chars)
            return page if page.text else None
        return None


async def _limited_body(response: httpx.Response, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        chunks.append(chunk)
        size += len(chunk)
        if size >= limit:
            break
    return b"".join(chunks)[:limit]
