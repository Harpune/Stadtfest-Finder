"""Brave Search API (ADR 0013): only the search query leaves the system."""

from __future__ import annotations

import httpx

from stadtfest.application.ai_ingestion.ports import SearchHit, WebSearchUnavailableError

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveWebSearch:
    """Implements `WebSearchPort` against the Brave Web Search API."""

    def __init__(self, client: httpx.AsyncClient, api_key: str) -> None:
        """Create the adapter.

        Args:
            client: HTTP client with a timeout.
            api_key: Subscription token (`WEB_SEARCH_API_KEY`).
        """
        self._client = client
        self._api_key = api_key

    async def search(self, query: str, count: int) -> list[SearchHit]:
        """German web results for the query."""
        try:
            response = await self._client.get(
                BRAVE_URL,
                params={
                    "q": query,
                    "count": min(count, 20),
                    "country": "DE",
                    "search_lang": "de",
                    "ui_lang": "de-DE",
                    "safesearch": "strict",
                },
                headers={"X-Subscription-Token": self._api_key, "Accept": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WebSearchUnavailableError from exc
        results = (body.get("web") or {}).get("results") or []
        return [
            SearchHit(
                url=str(item["url"]),
                title=str(item.get("title", "")),
                snippet=str(item.get("description", "")),
            )
            for item in results
            if isinstance(item, dict) and item.get("url")
        ]
