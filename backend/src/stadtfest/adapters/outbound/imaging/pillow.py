"""Image processing with Pillow (R08-US2).

The file type is detected from the content (Pillow reads the magic bytes), never from a
name or a declared content type. Variants are re-encoded from raw pixels, so no EXIF, XMP,
IPTC or ICC data of the original survives (GPS positions in particular).
"""

from __future__ import annotations

import asyncio
import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from stadtfest.application.moderation.image_ports import ProcessedImage, UnsupportedImageError
from stadtfest.domain.events.images import ImageFormat, Variant

_ACCEPTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
# Upper bound for decoded pixels (about 8,000 x 6,000); bigger files are rejected as bombs.
MAX_PIXELS = 50_000_000
_WEBP_QUALITY = 80
_JPEG_QUALITY = 82
_BACKGROUND = (255, 255, 255)


def _open(data: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(data))
            if image.format not in _ACCEPTED_FORMATS:
                raise UnsupportedImageError
            if image.width * image.height > MAX_PIXELS:
                raise UnsupportedImageError
            image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise UnsupportedImageError from None
    except (OSError, SyntaxError, ValueError):
        # Truncated or corrupt content.
        raise UnsupportedImageError from None
    return image


def _without_metadata(image: Image.Image) -> Image.Image:
    """Apply the EXIF orientation, flatten transparency, and copy only the pixels."""
    upright = ImageOps.exif_transpose(image)
    if upright.mode in ("RGBA", "LA") or (upright.mode == "P" and "transparency" in upright.info):
        rgba = upright.convert("RGBA")
        flat = Image.new("RGB", rgba.size, _BACKGROUND)
        flat.paste(rgba, mask=rgba.getchannel("A"))
        upright = flat
    rgb = upright.convert("RGB")
    return Image.frombytes("RGB", rgb.size, rgb.tobytes())


def _encode(image: Image.Image, image_format: ImageFormat) -> bytes:
    buffer = io.BytesIO()
    if image_format is ImageFormat.WEBP:
        image.save(buffer, "WEBP", quality=_WEBP_QUALITY, method=4)
    else:
        image.save(buffer, "JPEG", quality=_JPEG_QUALITY, optimize=True, progressive=True)
    return buffer.getvalue()


def process_sync(data: bytes) -> ProcessedImage:
    """Create all variants (blocking; run it in a thread).

    Raises:
        UnsupportedImageError: If the content is no JPEG, PNG or WebP image.
    """
    clean = _without_metadata(_open(data))
    files: dict[tuple[Variant, ImageFormat], bytes] = {}
    full_size = clean.size
    for variant in Variant:
        scaled = clean.copy()
        scaled.thumbnail((variant.max_edge, variant.max_edge), Image.Resampling.LANCZOS)
        if variant is Variant.FULL:
            full_size = scaled.size
        for image_format in ImageFormat:
            files[(variant, image_format)] = _encode(scaled, image_format)
    return ProcessedImage(width=full_size[0], height=full_size[1], files=files)


class PillowImageProcessor:
    """Implements `ImageProcessor`; the CPU work runs in a worker thread."""

    async def process(self, data: bytes) -> ProcessedImage:
        """Create all variants without metadata."""
        return await asyncio.to_thread(process_sync, data)
