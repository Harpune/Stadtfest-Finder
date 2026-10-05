"""Fake LLM for local development and tests: three finds from the fake search pages.

It calls the search tool like a real model would, so the pipeline (source check, search area,
duplicates) runs unchanged. Dates are relative to today, so finds are never in the past.
"""

from __future__ import annotations

from datetime import date, timedelta

from stadtfest.application.ai_ingestion.ports import FinderLimits, FinderResult, SearchTool
from stadtfest.domain.ai_ingestion.finds import FoundEvent


class FakeEventFinder:
    """Implements `EventFinder` without a provider."""

    async def find(
        self, system: str, prompt: str, search: SearchTool, limits: FinderLimits
    ) -> FinderResult:
        """Search once and turn the three fake pages into finds."""
        hits = await search("Feste Ostalb Herbst")
        today = date.today()
        by_title = {hit.title: hit.url for hit in hits}
        finds = [
            FoundEvent(
                name="Lichterfest Wasseralfingen",
                date_from=today + timedelta(days=20),
                date_to=today + timedelta(days=21),
                place="Karlstraße",
                address="Karlstraße 26, 73433 Aalen",
                source_url=by_title.get("Lichterfest Wasseralfingen", ""),
                lat=48.8655,
                lon=10.1005,
                category="Stadtfest",
                description="Laternen, Musik und Markt.",
            ),
            FoundEvent(
                name="Herbstmarkt im Stadtgarten",
                date_from=today + timedelta(days=12),
                date_to=today + timedelta(days=12),
                place="Stadtgarten",
                address="Stadtgarten, 73430 Aalen",
                source_url=by_title.get("Herbstmarkt im Stadtgarten Aalen", ""),
                category="Markt",
            ),
            FoundEvent(
                name="Ellwanger Brunnenfest",
                date_from=today + timedelta(days=30),
                date_to=today + timedelta(days=32),
                place="Marktplatz",
                address="Marktplatz 1, 73479 Ellwangen (Jagst)",
                source_url=by_title.get("Ellwanger Brunnenfest", ""),
                category="Stadtfest",
            ),
        ]
        return FinderResult(
            finds=[find for find in finds if find.source_url],
            input_tokens=0,
            output_tokens=0,
        )
