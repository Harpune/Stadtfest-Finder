"""Public URLs of image variants (R08-US4): read directly from the bucket's public prefix."""

from __future__ import annotations

from uuid import UUID

from stadtfest.application.events.views import ImageView
from stadtfest.domain.events.images import ImageFormat, Variant, variant_key


class ImageUrls:
    """Builds variant URLs from the public base URL of the bucket."""

    def __init__(self, public_base_url: str) -> None:
        """Create the builder.

        Args:
            public_base_url: URL under which the bucket is readable, e.g.
                `https://storage.example.eu/stadtfest-images`.
        """
        self._base = public_base_url.rstrip("/")

    def url(self, image_id: UUID, variant: Variant, image_format: ImageFormat) -> str:
        """URL of one variant."""
        return f"{self._base}/{variant_key(image_id, variant, image_format)}"

    def view(self, image_id: UUID, width: int | None, height: int | None) -> ImageView:
        """All variant URLs of a ready image."""
        return ImageView(
            url=self.url(image_id, Variant.FULL, ImageFormat.WEBP),
            thumb_url=self.url(image_id, Variant.THUMB, ImageFormat.WEBP),
            card_url=self.url(image_id, Variant.CARD, ImageFormat.WEBP),
            jpeg_url=self.url(image_id, Variant.FULL, ImageFormat.JPEG),
            width=width,
            height=height,
        )
