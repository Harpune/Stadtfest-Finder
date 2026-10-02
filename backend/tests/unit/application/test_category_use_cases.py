from uuid import uuid4

import pytest

from stadtfest.application.moderation.categories import (
    CreateCategory,
    DeleteCategory,
    ListModCategories,
    ModCategoryView,
    OrderCategories,
    UpdateCategory,
)
from stadtfest.application.outbox.ports import OutboxMessage
from stadtfest.application.outbox.use_cases import HandleDomainEvent
from stadtfest.application.shared.errors import ForbiddenError, InvalidInputError, NotFoundError
from stadtfest.domain.events.category import CategoryDraft
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import FakeCache, FakeCategoryRepository, FakeEventFavorites

ADMIN = Principal("a", frozenset({Role.USER, Role.MODERATOR, Role.CATEGORY_ADMIN}), "ostalb")
MODERATOR = Principal("m", frozenset({Role.USER, Role.MODERATOR}), "ostalb")
USER = Principal("u", frozenset({Role.USER}))
STADTFEST = ModCategoryView(uuid4(), "Stadtfest", "🎪", "#FFB547", True, 0, 0)
VOLKSFEST = ModCategoryView(uuid4(), "Volksfest & Kirmes", "🎡", "#FF6B8B", True, 1, 0)
WEIN = ModCategoryView(uuid4(), "Weinfest", "🍷", "#C792EA", False, 2, 0)


@pytest.fixture
def repo() -> FakeCategoryRepository:
    return FakeCategoryRepository(
        categories=[STADTFEST, VOLKSFEST, WEIN], events={STADTFEST.id: 3, VOLKSFEST.id: 2}
    )


async def test_moderators_read_including_inactive_with_counts(repo: FakeCategoryRepository) -> None:
    rows = await ListModCategories(repo)(MODERATOR)

    assert [(r.name, r.active, r.event_count) for r in rows] == [
        ("Stadtfest", True, 3),
        ("Volksfest & Kirmes", True, 2),
        ("Weinfest", False, 0),
    ]
    with pytest.raises(ForbiddenError):
        await ListModCategories(repo)(USER)


async def test_writing_needs_category_admin(repo: FakeCategoryRepository) -> None:
    draft = CategoryDraft("Herbstmarkt", "🎃", "#FFB547")
    with pytest.raises(ForbiddenError):
        await CreateCategory(repo)(MODERATOR, draft)
    with pytest.raises(ForbiddenError):
        await UpdateCategory(repo)(MODERATOR, STADTFEST.id, active=False)
    with pytest.raises(ForbiddenError):
        await OrderCategories(repo)(MODERATOR, [WEIN.id, STADTFEST.id, VOLKSFEST.id])
    with pytest.raises(ForbiddenError):
        await DeleteCategory(repo)(MODERATOR, WEIN.id, None)
    assert repo.outbox == []


async def test_create_appends_and_normalizes(repo: FakeCategoryRepository) -> None:
    created = await CreateCategory(repo)(ADMIN, CategoryDraft(" Herbstmarkt ", "🎃", "#ffb547"))

    assert (created.name, created.color, created.sort_order) == ("Herbstmarkt", "#FFB547", 3)
    assert repo.outbox == ["category.changed"]


@pytest.mark.parametrize(
    ("name", "problem"), [("", "required"), ("stadtFEST", "duplicate"), ("x" * 41, "too_long")]
)
async def test_names_are_required_short_and_unique(
    repo: FakeCategoryRepository, name: str, problem: str
) -> None:
    with pytest.raises(InvalidInputError) as error:
        await CreateCategory(repo)(ADMIN, CategoryDraft(name, "🎃", "#FFB547"))
    assert error.value.fields == {"name": problem}


async def test_update_changes_only_given_fields(repo: FakeCategoryRepository) -> None:
    updated = await UpdateCategory(repo)(ADMIN, VOLKSFEST.id, active=False)

    assert (updated.name, updated.emoji, updated.active) == ("Volksfest & Kirmes", "🎡", False)
    with pytest.raises(InvalidInputError):
        await UpdateCategory(repo)(ADMIN, VOLKSFEST.id, name="Stadtfest")
    with pytest.raises(NotFoundError):
        await UpdateCategory(repo)(ADMIN, uuid4(), active=True)


async def test_order_needs_the_complete_list(repo: FakeCategoryRepository) -> None:
    ordered = await OrderCategories(repo)(ADMIN, [WEIN.id, STADTFEST.id, VOLKSFEST.id])

    assert [c.name for c in ordered] == ["Weinfest", "Stadtfest", "Volksfest & Kirmes"]
    with pytest.raises(InvalidInputError):
        await OrderCategories(repo)(ADMIN, [WEIN.id, STADTFEST.id])


async def test_delete_without_events_needs_no_replacement(repo: FakeCategoryRepository) -> None:
    result = await DeleteCategory(repo)(ADMIN, WEIN.id, None)

    assert result.moved_events == 0
    assert await repo.get(WEIN.id) is None


async def test_delete_with_events_moves_them_to_the_replacement(
    repo: FakeCategoryRepository,
) -> None:
    with pytest.raises(InvalidInputError) as error:
        await DeleteCategory(repo)(ADMIN, VOLKSFEST.id, None)
    assert error.value.code == "replacement_required"

    result = await DeleteCategory(repo)(ADMIN, VOLKSFEST.id, STADTFEST.id)

    assert (result.moved_events, result.replacement_id) == (2, STADTFEST.id)
    assert repo.events[STADTFEST.id] == 5


@pytest.mark.parametrize("replacement", ["self", "unknown"])
async def test_delete_rejects_invalid_replacements(
    repo: FakeCategoryRepository, replacement: str
) -> None:
    target = VOLKSFEST.id if replacement == "self" else uuid4()
    with pytest.raises(InvalidInputError) as error:
        await DeleteCategory(repo)(ADMIN, VOLKSFEST.id, target)
    assert error.value.code == "invalid_replacement"


async def test_category_changes_invalidate_chips_and_catalog() -> None:
    async def ignore(*_args: object) -> None:
        return None

    cache = FakeCache()
    handle = HandleDomainEvent(cache, FakeEventFavorites(), ignore, ignore)
    await handle(OutboxMessage(uuid4(), "category.changed", {"categoryId": str(uuid4())}))

    assert await cache.generation("categories") == 1
    assert await cache.generation("catalog") == 1
