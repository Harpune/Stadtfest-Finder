"""Regions: a moderator region is a set of postal codes (decision E-05)."""

from __future__ import annotations

from dataclasses import dataclass

from stadtfest.domain.events.geo import PostalCode


@dataclass(frozen=True, slots=True)
class Region:
    """A moderation region."""

    key: str
    name: str
    postal_codes: frozenset[str]

    def contains(self, postal_code: PostalCode | str) -> bool:
        """Return True if the postal code belongs to this region."""
        return str(postal_code) in self.postal_codes
