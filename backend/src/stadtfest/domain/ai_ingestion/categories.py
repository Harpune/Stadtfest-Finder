"""Map the category an LLM names to an active category (R10-US3 step 8)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from uuid import UUID

# Lower-case words that mean an existing category; matched against the category names.
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "stadtfest": ("stadtfest", "altstadtfest", "dorffest", "straßenfest", "bürgerfest"),
    "volksfest": ("volksfest", "kirmes", "kerwe", "kirchweih", "jahrmarkt", "rummel", "kirbe"),
    "weihnachtsmarkt": ("weihnachtsmarkt", "christkindlesmarkt", "adventsmarkt"),
    "markt": ("markt", "messe", "flohmarkt", "bauernmarkt", "krämermarkt"),
    "weinfest": ("weinfest", "weinmarkt", "winzerfest"),
}


def map_category(named: str | None, active: Mapping[str, UUID]) -> UUID | None:
    """The active category for a named one, or None without a safe match.

    Args:
        named: What the LLM wrote, e.g. "Kirmes".
        active: Active category names → IDs.
    """
    if not named:
        return None
    wanted = named.strip().lower()
    by_name = {name.lower(): category_id for name, category_id in active.items()}
    if wanted in by_name:
        return by_name[wanted]
    for synonyms in _SYNONYMS.values():
        if wanted in synonyms:
            # Whole words only: "markt" means "Markt & Messe", not "Weihnachtsmarkt".
            matches = [
                category_id
                for name, category_id in by_name.items()
                if set(re.findall(r"[a-zäöüß]+", name)) & set(synonyms)
            ]
            if len(matches) == 1:
                return matches[0]
    return None
