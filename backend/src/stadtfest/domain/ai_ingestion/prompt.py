"""Prompt of the AI search: only public parameters (R10-US3 step 2, privacy).

Prompts are versioned templates (`v1`, `v2`, ...). A template may only use the
placeholders in `PLACEHOLDERS`, all of them public values derived from the postal code;
`PromptTemplate` rejects anything else, so no moderator or user data can reach the LLM.
Snapshot tests guard the rendered text.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from datetime import date

PLACEHOLDERS = frozenset(
    {
        "postal_code",
        "place_name",
        "radius_km",
        "date_from",
        "date_to",
        "years",
        "categories",
        "nearby_places",
    }
)


class InvalidPromptError(ValueError):
    """A prompt template uses an unknown placeholder or has no user part."""


@dataclass(frozen=True, slots=True)
class SearchParameters:
    """Everything the LLM may see."""

    postal_code: str
    place_name: str
    radius_km: int
    date_from: date
    date_to: date
    categories: tuple[str, ...]
    # Towns within the radius (public place names from the geocoder, nearest first).
    nearby_places: tuple[str, ...] = ()

    def values(self) -> dict[str, str]:
        """Placeholder values; dates in ISO format, lists comma-separated."""
        years = sorted({self.date_from.year, self.date_to.year})
        return {
            "postal_code": self.postal_code,
            "place_name": self.place_name,
            "radius_km": str(self.radius_km),
            "date_from": self.date_from.isoformat(),
            "date_to": self.date_to.isoformat(),
            "years": "/".join(str(year) for year in years),
            "categories": ", ".join(self.categories) or "alle",
            "nearby_places": ", ".join(self.nearby_places) or self.place_name,
        }


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    """System and user prompt of one search."""

    system: str
    user: str


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """A versioned prompt with `{placeholder}` fields.

    Raises:
        InvalidPromptError: On construction, if a placeholder is not allowed or the user
            part is empty.
    """

    version: str
    system: str
    user: str

    def __post_init__(self) -> None:
        """Validate the placeholders of both parts."""
        if not self.user.strip():
            raise InvalidPromptError(f"prompt {self.version}: user part is empty")
        for part in (self.system, self.user):
            unknown = _placeholders(part) - PLACEHOLDERS
            if unknown:
                raise InvalidPromptError(
                    f"prompt {self.version}: unknown placeholders {sorted(unknown)}"
                )

    def render(self, parameters: SearchParameters) -> RenderedPrompt:
        """Fill in the parameters."""
        values = parameters.values()
        return RenderedPrompt(
            system=self.system.format_map(values).strip(),
            user=self.user.format_map(values).strip(),
        )


def _placeholders(text: str) -> set[str]:
    try:
        fields = string.Formatter().parse(text)
        return {name for _, name, _, _ in fields if name is not None}
    except ValueError as error:  # unbalanced braces
        raise InvalidPromptError(str(error)) from None


SYSTEM_MARKER = "<!-- system -->"
USER_MARKER = "<!-- user -->"


def parse_prompt(version: str, text: str) -> PromptTemplate:
    """Read a prompt file: the parts follow `<!-- system -->` and `<!-- user -->`.

    Text before the first marker is a comment for humans and is ignored.

    Raises:
        InvalidPromptError: If a marker is missing or a placeholder is not allowed.
    """
    if SYSTEM_MARKER not in text or USER_MARKER not in text:
        raise InvalidPromptError(f"prompt {version}: needs {SYSTEM_MARKER} and {USER_MARKER}")
    _, rest = text.split(SYSTEM_MARKER, 1)
    system, user = rest.split(USER_MARKER, 1)
    return PromptTemplate(version, system.strip(), user.strip())
