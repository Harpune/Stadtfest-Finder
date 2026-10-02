from uuid import uuid4

import pytest

from stadtfest.domain.events.images import (
    MAX_IMAGES_PER_EVENT,
    MAX_UPLOAD_BYTES,
    ImageFormat,
    InvalidOrderError,
    TooManyImagesError,
    Variant,
    all_variant_keys,
    check_order,
    insert_position,
    upload_key,
    upload_problems,
    variant_key,
)


@pytest.mark.parametrize("content_type", ["image/jpeg", "image/png", "image/webp"])
def test_supported_types_up_to_10_mb_are_accepted(content_type: str) -> None:
    assert upload_problems(content_type, MAX_UPLOAD_BYTES) == {}


def test_other_types_and_sizes_are_rejected() -> None:
    assert upload_problems("image/gif", 10) == {"contentType": "unsupported_type"}
    assert upload_problems("image/jpeg", MAX_UPLOAD_BYTES + 1) == {"sizeBytes": "too_large"}
    assert upload_problems("image/jpeg", 0) == {"sizeBytes": "empty"}


def test_new_images_are_appended_unless_a_position_is_given() -> None:
    assert insert_position(3, None) == 3
    assert insert_position(3, 0) == 0
    assert insert_position(3, 9) == 3


def test_at_most_12_images_per_event() -> None:
    assert insert_position(MAX_IMAGES_PER_EVENT - 1, None) == MAX_IMAGES_PER_EVENT - 1
    with pytest.raises(TooManyImagesError):
        insert_position(MAX_IMAGES_PER_EVENT, None)


def test_order_must_be_the_complete_list_once() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    check_order([a, b, c], [c, a, b])
    for wrong in ([a, b], [a, b, b], [a, b, c, uuid4()], [a, b, uuid4()]):
        with pytest.raises(InvalidOrderError):
            check_order([a, b, c], wrong)


def test_keys_contain_only_ids() -> None:
    image_id, upload_id = uuid4(), uuid4()
    assert upload_key(upload_id) == f"uploads/{upload_id}"
    assert (
        variant_key(image_id, Variant.THUMB, ImageFormat.WEBP)
        == f"public/images/{image_id}/thumb.webp"
    )
    keys = all_variant_keys(image_id)
    assert len(keys) == 6
    assert all(key.startswith(f"public/images/{image_id}/") for key in keys)


def test_variant_sizes() -> None:
    assert [v.max_edge for v in Variant] == [1600, 600, 200]
