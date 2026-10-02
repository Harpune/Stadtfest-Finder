"""Fake web search for local development and tests: fixed pages around Aalen."""

from __future__ import annotations

from stadtfest.application.ai_ingestion.ports import SearchHit

FAKE_PAGES = (
    SearchHit(
        "https://www.wasseralfingen.example/lichterfest",
        "Lichterfest Wasseralfingen",
        "Laternen, Musik und Markt rund um die Karlstraße.",
    ),
    SearchHit(
        "https://www.aalen.example/stadtgarten-herbstmarkt",
        "Herbstmarkt im Stadtgarten Aalen",
        "Regionale Händler, Kürbisse und Most.",
    ),
    SearchHit(
        "https://www.ellwangen.example/brunnenfest",
        "Ellwanger Brunnenfest",
        "Fest rund um den Marktbrunnen mit Musik und Bewirtung.",
    ),
)


class FakeWebSearch:
    """Returns the same three pages for every query; no network access."""

    async def search(self, query: str, count: int) -> list[SearchHit]:
        """The fixed pages."""
        return list(FAKE_PAGES[:count])
