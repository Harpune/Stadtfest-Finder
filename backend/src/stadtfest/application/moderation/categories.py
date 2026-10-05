"""App-wide category maintenance (R09).

`moderator` and `category_admin` read; only `category_admin` writes. Every change writes
`category.changed` to the outbox in the same transaction (ADR 0005); its consumer
invalidates the cached public category list and the catalog.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from stadtfest.application.shared.errors import ForbiddenError, InvalidInputError, NotFoundError
from stadtfest.domain.events.category import (
    CategoryDraft,
    InvalidCategoryOrderError,
    category_problems,
    check_category_order,
)
from stadtfest.domain.identity.principal import Principal, Role

REPLACEMENT_REQUIRED = "replacement_required"
INVALID_REPLACEMENT = "invalid_replacement"


@dataclass(frozen=True, slots=True)
class ModCategoryView:
    """A category with its number of events (not deleted)."""

    id: UUID
    name: str
    emoji: str
    color: str
    active: bool
    sort_order: int
    event_count: int


class DuplicateCategoryNameError(Exception):
    """Another category already has this name (ignoring case)."""


class CategoryInUseError(Exception):
    """Events still use the category and no replacement was given."""


class CategoryRepository(Protocol):
    """Categories in the database; changes write `category.changed` to the outbox."""

    async def list_all(self) -> list[ModCategoryView]:
        """All categories in chip order, with event counts."""
        ...

    async def get(self, category_id: UUID) -> ModCategoryView | None:
        """One category, or None."""
        ...

    async def add(self, category_id: UUID, draft: CategoryDraft) -> ModCategoryView:
        """Insert at the end of the order.

        Raises:
            DuplicateCategoryNameError: If the name is taken.
        """
        ...

    async def update(self, category_id: UUID, draft: CategoryDraft) -> ModCategoryView | None:
        """Store all fields; None if the category does not exist.

        Raises:
            DuplicateCategoryNameError: If the name is taken.
        """
        ...

    async def reorder(self, category_ids: Sequence[UUID]) -> None:
        """Set `sort_order` 0..n-1 in the given order."""
        ...

    async def delete(self, category_id: UUID, replacement_id: UUID | None) -> int | None:
        """Move the events (also deleted ones) and delete, in one transaction.

        Returns:
            The number of moved events, or None if the category does not exist.

        Raises:
            CategoryInUseError: If events use it and `replacement_id` is None.
        """
        ...


def _require_reader(principal: Principal) -> None:
    if not (principal.has_role(Role.MODERATOR) or principal.has_role(Role.CATEGORY_ADMIN)):
        raise ForbiddenError


def _require_admin(principal: Principal) -> None:
    if not principal.has_role(Role.CATEGORY_ADMIN):
        raise ForbiddenError


def _checked(draft: CategoryDraft) -> CategoryDraft:
    problems = category_problems(draft)
    if problems:
        raise InvalidInputError(problems)
    return draft.normalized()


class _Categories:
    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories


class ListModCategories(_Categories):
    """Overview including inactive categories (R09-US1)."""

    async def __call__(self, principal: Principal) -> list[ModCategoryView]:
        """Return all categories in chip order."""
        _require_reader(principal)
        return await self._categories.list_all()


class CreateCategory(_Categories):
    """New category at the end of the order (R09-US3)."""

    async def __call__(self, principal: Principal, draft: CategoryDraft) -> ModCategoryView:
        """Create the category.

        Raises:
            InvalidInputError: Missing, too long or duplicate name, or no preset emoji/color.
        """
        _require_admin(principal)
        try:
            return await self._categories.add(uuid4(), _checked(draft))
        except DuplicateCategoryNameError:
            raise InvalidInputError({"name": "duplicate"}) from None


class UpdateCategory(_Categories):
    """Change name, emoji, color or the active flag (R09-US3)."""

    async def __call__(
        self,
        principal: Principal,
        category_id: UUID,
        *,
        name: str | None = None,
        emoji: str | None = None,
        color: str | None = None,
        active: bool | None = None,
    ) -> ModCategoryView:
        """Apply the given fields.

        Raises:
            NotFoundError: Unknown category.
            InvalidInputError: As for creating.
        """
        _require_admin(principal)
        current = await self._categories.get(category_id)
        if current is None:
            raise NotFoundError
        draft = CategoryDraft(
            name=current.name if name is None else name,
            emoji=current.emoji if emoji is None else emoji,
            color=current.color if color is None else color,
            active=current.active if active is None else active,
        )
        try:
            updated = await self._categories.update(category_id, _checked(draft))
        except DuplicateCategoryNameError:
            raise InvalidInputError({"name": "duplicate"}) from None
        if updated is None:
            raise NotFoundError
        return updated


class OrderCategories(_Categories):
    """Chip order by drag and drop (R09-US2)."""

    async def __call__(
        self, principal: Principal, category_ids: Sequence[UUID]
    ) -> list[ModCategoryView]:
        """Apply the complete new order.

        Raises:
            InvalidInputError: An ID is missing, unknown or repeated.
        """
        _require_admin(principal)
        current = [category.id for category in await self._categories.list_all()]
        try:
            check_category_order(current, category_ids)
        except InvalidCategoryOrderError:
            raise InvalidInputError({"ids": "invalid_order"}) from None
        await self._categories.reorder(category_ids)
        return await self._categories.list_all()


@dataclass(frozen=True, slots=True)
class CategoryDeletion:
    """Result of deleting a category."""

    moved_events: int
    replacement_id: UUID | None


class DeleteCategory(_Categories):
    """Delete, moving the events to a replacement category (R09-US4)."""

    async def __call__(
        self, principal: Principal, category_id: UUID, replacement_id: UUID | None
    ) -> CategoryDeletion:
        """Delete the category.

        Raises:
            NotFoundError: Unknown category.
            InvalidInputError: `replacement_required` or `invalid_replacement`.
        """
        _require_admin(principal)
        if replacement_id is not None and (
            replacement_id == category_id or await self._categories.get(replacement_id) is None
        ):
            raise InvalidInputError({"replacementId": INVALID_REPLACEMENT}, INVALID_REPLACEMENT)
        try:
            moved = await self._categories.delete(category_id, replacement_id)
        except CategoryInUseError:
            raise InvalidInputError(
                {"replacementId": REPLACEMENT_REQUIRED}, REPLACEMENT_REQUIRED
            ) from None
        if moved is None:
            raise NotFoundError
        return CategoryDeletion(moved, replacement_id)
