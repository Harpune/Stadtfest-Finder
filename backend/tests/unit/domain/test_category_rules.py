from uuid import uuid4

import pytest

from stadtfest.domain.events.category import (
    CategoryDraft,
    InvalidCategoryOrderError,
    category_problems,
    check_category_order,
)


def test_valid_category_has_no_problems() -> None:
    assert category_problems(CategoryDraft("Weinfest", "🍷", "#c792ea")) == {}


def test_name_emoji_and_color_are_checked() -> None:
    assert category_problems(CategoryDraft("  ", "🦄", "#123456")) == {
        "name": "required",
        "emoji": "not_allowed",
        "color": "not_allowed",
    }
    assert category_problems(CategoryDraft("x" * 41, "🍷", "#C792EA")) == {"name": "too_long"}


def test_normalized_trims_and_uppercases() -> None:
    draft = CategoryDraft("  Weinfest ", "🍷", "#c792ea").normalized()
    assert (draft.name, draft.color) == ("Weinfest", "#C792EA")


def test_order_must_list_every_category_once() -> None:
    a, b = uuid4(), uuid4()
    check_category_order([a, b], [b, a])
    for wrong in ([a], [a, a], [a, b, uuid4()]):
        with pytest.raises(InvalidCategoryOrderError):
            check_category_order([a, b], wrong)
