"""Tests for the Pillow image processor (R08-US2), including the EXIF GPS check (DoD)."""

from __future__ import annotations

import io

import pytest
from PIL import ExifTags, Image

from stadtfest.adapters.outbound.imaging.pillow import PillowImageProcessor
from stadtfest.application.moderation.image_ports import UnsupportedImageError
from stadtfest.domain.events.images import ImageFormat, Variant


def _jpeg_with_gps(width: int = 3000, height: int = 2000, orientation: int = 1) -> bytes:
    image = Image.new("RGB", (width, height), (200, 40, 90))
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "TestCam"
    exif[ExifTags.Base.Orientation] = orientation
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N"
    gps[ExifTags.GPS.GPSLatitude] = (48.0, 50.0, 12.0)
    gps[ExifTags.GPS.GPSLongitudeRef] = "E"
    gps[ExifTags.GPS.GPSLongitude] = (10.0, 5.0, 30.0)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif, xmp=b"<x:xmpmeta>secret</x:xmpmeta>")
    return buffer.getvalue()


async def test_variants_carry_no_metadata_at_all() -> None:
    original = _jpeg_with_gps()
    assert Image.open(io.BytesIO(original)).getexif().get_ifd(ExifTags.IFD.GPSInfo)

    result = await PillowImageProcessor().process(original)

    assert len(result.files) == 6
    for content in result.files.values():
        variant = Image.open(io.BytesIO(content))
        assert not variant.getexif()
        assert "exif" not in variant.info
        assert "xmp" not in variant.info
        assert b"secret" not in content
        assert b"TestCam" not in content


async def test_variants_are_scaled_to_their_longest_edge() -> None:
    result = await PillowImageProcessor().process(_jpeg_with_gps(3000, 2000))

    assert (result.width, result.height) == (1600, 1067)
    for variant in Variant:
        for image_format in ImageFormat:
            size = Image.open(io.BytesIO(result.files[(variant, image_format)])).size
            assert max(size) == variant.max_edge


async def test_small_images_are_not_upscaled() -> None:
    result = await PillowImageProcessor().process(_jpeg_with_gps(400, 300))

    assert (result.width, result.height) == (400, 300)
    thumb = Image.open(io.BytesIO(result.files[(Variant.THUMB, ImageFormat.WEBP)]))
    assert thumb.size == (200, 150)


async def test_exif_orientation_is_applied_before_stripping() -> None:
    # Orientation 6: the camera was turned; the stored pixels are landscape.
    result = await PillowImageProcessor().process(_jpeg_with_gps(3000, 2000, orientation=6))

    assert (result.width, result.height) == (1067, 1600)


@pytest.mark.parametrize("fmt", ["PNG", "WEBP"])
async def test_png_and_webp_with_transparency_are_flattened(fmt: str) -> None:
    buffer = io.BytesIO()
    Image.new("RGBA", (800, 400), (0, 0, 0, 0)).save(buffer, fmt)

    result = await PillowImageProcessor().process(buffer.getvalue())

    jpeg = Image.open(io.BytesIO(result.files[(Variant.FULL, ImageFormat.JPEG)]))
    assert jpeg.mode == "RGB"
    assert jpeg.getpixel((10, 10)) == pytest.approx((255, 255, 255), abs=3)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "content",
    [b"not an image", b"GIF89a" + b"\x00" * 100, b"\xff\xd8\xff\xe0" + b"\x00" * 50],
    ids=["text", "gif", "truncated-jpeg"],
)
async def test_other_content_is_rejected(content: bytes) -> None:
    with pytest.raises(UnsupportedImageError):
        await PillowImageProcessor().process(content)


async def test_gif_files_are_rejected_by_content() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (50, 50)).save(buffer, "GIF")
    with pytest.raises(UnsupportedImageError):
        await PillowImageProcessor().process(buffer.getvalue())
