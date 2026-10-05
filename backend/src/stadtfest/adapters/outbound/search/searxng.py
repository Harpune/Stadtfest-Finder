"""Self-hosted SearXNG (ADR 0013): the own server asks the search engines, no API key."""

from __future__ import annotations

import asyncio

import httpx

from stadtfest.application.ai_ingestion.ports import SearchHit, WebSearchUnavailableError

# Models send several searches at once (prompt v2); eight parallel queries made Google and
# others answer with CAPTCHAs (05.10.2026).
MAX_PARALLEL = 2


class SearxngWebSearch:
    """Implements `WebSearchPort` against the JSON API of a SearXNG instance."""

    def __init__(
        self, client: httpx.AsyncClient, base_url: str, max_parallel: int = MAX_PARALLEL
    ) -> None:
        """Create the adapter.

        Args:
            client: HTTP client with a timeout.
            base_url: Instance root (`WEB_SEARCH_BASE_URL`); `format: json` must be enabled.
            max_parallel: Concurrent requests; more make the upstream engines block.
        """
        self._client = client
        self._url = base_url.rstrip("/") + "/search"
        self._slots = asyncio.Semaphore(max_parallel)

    async def search(self, query: str, count: int) -> list[SearchHit]:
        """German web results for the query, at most `count`."""
        async with self._slots:
            return await self._search(query, count)

    async def _search(self, query: str, count: int) -> list[SearchHit]:
        try:
            response = await self._client.get(
                self._url,
                params={
                    "q": query,
                    "format": "json",
                    "categories": "general",
                    "language": "de-DE",
                    "safesearch": 2,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WebSearchUnavailableError from exc
        if not isinstance(body, dict):
            raise WebSearchUnavailableError
        results = body.get("results") or []
        # No results while engines failed means the upstream engines blocked or timed out
        # (e.g. CAPTCHA); report that instead of an empty search.
        if not results and body.get("unresponsive_engines"):
            raise WebSearchUnavailableError
        hits = [
            SearchHit(
                url=str(item["url"]),
                title=str(item.get("title", "")),
                snippet=str(item.get("content", "")),
            )
            for item in results
            if isinstance(item, dict) and item.get("url")
        ]
        return hits[:count]
