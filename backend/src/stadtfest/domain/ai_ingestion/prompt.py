"""Prompt of the AI search: only public parameters (R10-US3 step 2, privacy).

The prompt is built by a pure function from `SearchParameters` only. It never contains
moderator data or user data; a snapshot test guards this.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class SearchParameters:
    """Everything the LLM may see."""

    postal_code: str
    place_name: str
    radius_km: int
    date_from: date
    date_to: date
    categories: tuple[str, ...]


SYSTEM_PROMPT = (
    "Du recherchierst öffentliche Veranstaltungen (Stadtfeste, Volksfeste, Kirmes, "
    "Weihnachtsmärkte, Märkte) in Deutschland. Nutze das Werkzeug `web_search`, um "
    "Quellen zu finden, und gib nur Veranstaltungen zurück, die du auf einer Seite aus den "
    "Suchergebnissen belegen kannst. `source_url` muss genau eine dieser Seiten sein. "
    "Erfinde nichts: Fehlt eine Angabe, lass das Feld leer. Daten im Format JJJJ-MM-TT."
)


def build_prompt(parameters: SearchParameters) -> str:
    """User prompt for one search."""
    categories = ", ".join(parameters.categories) or "alle"
    return (
        f"Finde Veranstaltungen im Umkreis von {parameters.radius_km} km um "
        f"{parameters.postal_code} {parameters.place_name}, die zwischen "
        f"{parameters.date_from.isoformat()} und {parameters.date_to.isoformat()} "
        f"stattfinden. Kategorien: {categories}. "
        "Gib für jede Veranstaltung Name, Beginn, Ende, Ort, Adresse, falls bekannt "
        "Koordinaten, die passende Kategorie, eine kurze Beschreibung und die Quelle an."
    ).strip()
