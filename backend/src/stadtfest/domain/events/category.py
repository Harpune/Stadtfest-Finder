"""Category rules: palette, emojis, fields and order (R09)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from uuid import UUID

# Colors moderators may choose (design reference, theme-farben.md).
CATEGORY_PALETTE = ("#FFB547", "#FF6B8B", "#5EEAD4", "#8B9CFF", "#7ED957", "#C792EA")

# Emojis moderators may choose (design reference §14).
CATEGORY_EMOJIS = ("🎪", "🎡", "🎄", "🐎", "🍺", "🍷", "🎭", "🎶", "🏰", "🎃", "🌸", "🔥")


def is_palette_color(color: str) -> bool:
    """Return True if `color` is one of the allowed category colors."""
    return color.upper() in CATEGORY_PALETTE


def is_allowed_emoji(emoji: str) -> bool:
    """Return True if `emoji` is one of the allowed category emojis."""
    return emoji in CATEGORY_EMOJIS


MAX_NAME_LENGTH = 40
CATEGORY_CHANGED = "category.changed"


class InvalidCategoryOrderError(Exception):
    """The new order is not a permutation of all categories."""


@dataclass(frozen=True, slots=True)
class CategoryDraft:
    """Editable fields of a category (R09-US3)."""

    name: str
    emoji: str
    color: str
    active: bool = True

    def normalized(self) -> CategoryDraft:
        """Trimmed name and upper-case color."""
        return replace(self, name=self.name.strip(), color=self.color.upper())


def category_problems(draft: CategoryDraft) -> dict[str, str]:
    """Field problems of a category; empty if it may be stored."""
    problems: dict[str, str] = {}
    if not draft.name.strip():
        problems["name"] = "required"
    elif len(draft.name.strip()) > MAX_NAME_LENGTH:
        problems["name"] = "too_long"
    if not is_allowed_emoji(draft.emoji):
        problems["emoji"] = "not_allowed"
    if not is_palette_color(draft.color):
        problems["color"] = "not_allowed"
    return problems


def check_category_order(current: Sequence[UUID], requested: Sequence[UUID]) -> None:
    """Require all category IDs exactly once (R09-US2).

    Raises:
        InvalidCategoryOrderError: If an ID is missing, unknown or repeated.
    """
    if len(requested) != len(set(requested)) or set(requested) != set(current):
        raise InvalidCategoryOrderError
