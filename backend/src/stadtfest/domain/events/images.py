"""Event images (R08): upload rules, order, variants and object keys.

Object keys contain only IDs, never names (R08-US4). Variants live under the public
prefix and never change, so they can be cached for a long time; originals stay private.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGES_PER_EVENT = 12
PUBLIC_PREFIX = "public/"


class ImageStatus(StrEnum):
    """Processing state of an event image."""

    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ImageEventType(StrEnum):
    """Image domain events written to the outbox (ADR 0005)."""

    UPLOADED = "image.uploaded"
    REMOVED = "image.removed"


class Variant(StrEnum):
    """Stored variants; the value is the longest edge in pixels (R08-US2)."""

    FULL = "full"
    CARD = "card"
    THUMB = "thumb"

    @property
    def max_edge(self) -> int:
        """Longest edge of the variant in pixels."""
        return _MAX_EDGES[self]


_MAX_EDGES = {Variant.FULL: 1600, Variant.CARD: 600, Variant.THUMB: 200}


class ImageFormat(StrEnum):
    """Output formats of every variant."""

    WEBP = "webp"
    JPEG = "jpg"


class TooManyImagesError(Exception):
    """The event already has the maximum number of images."""


class InvalidOrderError(Exception):
    """The new order is not a permutation of the event's images."""


def upload_problems(content_type: str, size_bytes: int) -> dict[str, str]:
    """Return field problems of an upload request; empty if it is acceptable."""
    problems: dict[str, str] = {}
    if content_type not in ALLOWED_CONTENT_TYPES:
        problems["contentType"] = "unsupported_type"
    if size_bytes < 1 or size_bytes > MAX_UPLOAD_BYTES:
        problems["sizeBytes"] = "too_large" if size_bytes > MAX_UPLOAD_BYTES else "empty"
    return problems


def insert_position(current_count: int, requested: int | None) -> int:
    """Position of a new image: appended unless a valid position is requested.

    Raises:
        TooManyImagesError: If the event already has `MAX_IMAGES_PER_EVENT` images.
    """
    if current_count >= MAX_IMAGES_PER_EVENT:
        raise TooManyImagesError
    if requested is None or requested > current_count:
        return current_count
    return max(requested, 0)


def check_order(current: Sequence[UUID], requested: Sequence[UUID]) -> None:
    """Require the complete list of the event's images, each exactly once (R08-US3).

    Raises:
        InvalidOrderError: If an ID is missing, unknown or repeated.
    """
    if len(requested) != len(set(requested)) or set(requested) != set(current):
        raise InvalidOrderError


def upload_key(upload_id: UUID) -> str:
    """Private key of an uploaded original."""
    return f"uploads/{upload_id}"


def variant_key(image_id: UUID, variant: Variant, image_format: ImageFormat) -> str:
    """Public, immutable key of one variant."""
    return f"{PUBLIC_PREFIX}images/{image_id}/{variant.value}.{image_format.value}"


def image_prefix(image_id: UUID) -> str:
    """Common prefix of all variants of one image."""
    return f"{PUBLIC_PREFIX}images/{image_id}/"


def all_variant_keys(image_id: UUID) -> list[str]:
    """Keys of every variant in every format."""
    return [variant_key(image_id, v, f) for v in Variant for f in ImageFormat]


@dataclass(frozen=True, slots=True)
class EventImage:
    """An image of an event as stored."""

    id: UUID
    event_id: UUID
    upload_id: UUID | None
    position: int
    status: ImageStatus
    width: int | None = None
    height: int | None = None
