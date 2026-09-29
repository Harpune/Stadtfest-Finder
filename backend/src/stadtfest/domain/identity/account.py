"""Rules for user account data (R05). The email address is never stored (E-08)."""

from __future__ import annotations

NAME_MAX_LENGTH = 50


class InvalidNameError(ValueError):
    """A first or last name violates the length rules."""


def normalize_name(value: str) -> str:
    """Trim a name entered by the user and check its length (1-50 characters).

    Args:
        value: Raw input.

    Returns:
        The trimmed name.

    Raises:
        InvalidNameError: If the trimmed name is empty or longer than 50 characters.
    """
    trimmed = value.strip()
    if not 1 <= len(trimmed) <= NAME_MAX_LENGTH:
        raise InvalidNameError
    return trimmed


def name_from_claim(value: str | None) -> str:
    """Derive a stored name from an IdP claim; missing names are stored as empty string.

    Over-long claim values are truncated instead of rejected, because the user cannot
    fix them in the app before the account exists.

    Args:
        value: Claim value (`given_name` or `family_name`) or None.

    Returns:
        The trimmed, possibly empty name with at most 50 characters.
    """
    return (value or "").strip()[:NAME_MAX_LENGTH].strip()
