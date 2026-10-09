"""Friendships via a personal friend link (R12, E-02).

The link token is 128 random bits (base64url, 22 characters) without personal data. Whoever
holds the link may befriend its owner: the link itself is the owner's consent.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from enum import StrEnum

TOKEN_BYTES = 16
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{22}$")
# Lookups and accepts per user and hour (protection against guessing tokens).
LOOKUP_LIMIT = 20
LOOKUP_WINDOW_SECONDS = 3600


class FriendEventType(StrEnum):
    """Domain events of friendships (outbox, ADR 0005); payloads carry user IDs only."""

    CREATED = "friendship.created"


def new_token() -> str:
    """A fresh link token: 128 random bits, base64url without padding."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def is_token(value: str) -> bool:
    """Whether the value has the token format (cheap check before any lookup)."""
    return bool(_TOKEN.match(value))


@dataclass(frozen=True, slots=True)
class LinkOwner:
    """What someone with the link may see of its owner: first name and last-name initial."""

    first_name: str
    last_name_initial: str

    @classmethod
    def of(cls, first_name: str, last_name: str) -> LinkOwner:
        """Shorten the last name to its initial."""
        return cls(first_name, last_name.strip()[:1].upper())
