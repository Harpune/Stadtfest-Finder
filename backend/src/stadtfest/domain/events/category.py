"""Category palette rules."""

from __future__ import annotations

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
