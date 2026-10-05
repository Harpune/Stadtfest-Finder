"""Reading result pages for the LLM (R10b-US5) with the SSRF protection of the source check.

Only HTML and plain text are read, at most `MAX_BYTES`; scripts, styles and navigation are
dropped and the visible text is shortened to the requested length. No cookies, redirects
are followed manually so every host is checked.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

from stadtfest.adapters.outbound.sources.http import is_public_host

MAX_BYTES = 1_500_000
MAX_REDIRECTS = 3
_TEXT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
_SKIPPED = frozenset({"script", "style", "noscript", "svg", "template", "iframe", "nav"})
_BLOCKS = frozenset(
    {
        "p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article", "header",
        "footer", "main", "aside", "h1", "h2", "h3", "h4", "h5", "h6", "dt", "dd", "title",
    }
)  # fmt: skip


class _TextExtractor(HTMLParser):
    """Visible text with line breaks at block elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED:
            self._skip_depth += 1
        elif tag in _BLOCKS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED and self._skip_depth:
            self._skip_depth -= 1
        elif tag in _BLOCKS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        lines = (re.sub(r"\s+", " ", line).strip() for line in "".join(self._parts).split("\n"))
        result: list[str] = []
        for line in lines:
            if line and (not result or result[-1] != line):
                result.append(line)
        return "\n".join(result)


def html_to_text(html: str) -> str:
    """Visible text of an HTML document, one block per line."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return parser.text()


class HttpPageReader:
    """Implements `PageReader` with GET, public hosts only, size and type limits."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Create the reader.

        Args:
            client: HTTP client without cookies that does not follow redirects itself.
        """
        self._client = client

    async def read(self, url: str, max_chars: int) -> str | None:
        """Visible text of the page, at most `max_chars`; None if it cannot be read."""
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
                    if not content_type.startswith(_TEXT_TYPES):
                        return None
                    body = await _limited_body(response)
                    text = body.decode(response.encoding or "utf-8", errors="replace")
            except httpx.HTTPError:
                return None
            if not content_type.startswith("text/plain"):
                text = html_to_text(text)
            return text[:max_chars] or None
        return None


async def _limited_body(response: httpx.Response) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        chunks.append(chunk)
        size += len(chunk)
        if size >= MAX_BYTES:
            break
    return b"".join(chunks)[:MAX_BYTES]
