"""Shared lists (R13): rules for names and the domain events of a list."""

from __future__ import annotations

from enum import StrEnum

NAME_MAX = 60
MEMBERS_MAX = 50
NOT_A_FRIEND = "not_a_friend"


class ListEventType(StrEnum):
    """Domain events of shared lists (outbox, ADR 0005); payloads carry IDs only."""

    MEMBERS_ADDED = "list.members_added"


class InvalidListNameError(ValueError):
    """The name is empty or longer than `NAME_MAX` after trimming."""


def clean_name(name: str) -> str:
    """The trimmed name.

    Raises:
        InvalidListNameError: If it is empty or too long.
    """
    cleaned = " ".join(name.split())
    if not 0 < len(cleaned) <= NAME_MAX:
        raise InvalidListNameError(name)
    return cleaned
