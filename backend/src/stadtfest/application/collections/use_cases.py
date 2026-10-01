"""Favorite use cases (R06-US1, US2)."""

from __future__ import annotations

from uuid import UUID

from stadtfest.application.collections.ports import (
    AccountResolver,
    FavoriteRepository,
    FavoriteView,
)
from stadtfest.application.shared.errors import NotFoundError
from stadtfest.application.shared.ports import Clock
from stadtfest.domain.identity.principal import Principal


class AddFavorite:
    """Mark an event as favorite (idempotent)."""

    def __init__(self, favorites: FavoriteRepository, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._favorites = favorites
        self._accounts = accounts

    async def __call__(self, principal: Principal, event_id: UUID) -> None:
        """Add the favorite.

        Raises:
            NotFoundError: If the event is not publicly visible.
        """
        await self._accounts(principal)
        if not await self._favorites.add(principal.subject, event_id):
            raise NotFoundError


class RemoveFavorite:
    """Remove an event from the favorites (idempotent)."""

    def __init__(self, favorites: FavoriteRepository) -> None:
        """Create the use case."""
        self._favorites = favorites

    async def __call__(self, principal: Principal, event_id: UUID) -> None:
        """Remove the favorite; succeeds also if there was none."""
        await self._favorites.remove(principal.subject, event_id)


class ListFavorites:
    """Favorites of the caller for the timeline."""

    def __init__(self, favorites: FavoriteRepository, clock: Clock) -> None:
        """Create the use case."""
        self._favorites = favorites
        self._clock = clock

    async def __call__(self, principal: Principal, *, include_past: bool) -> list[FavoriteView]:
        """Return upcoming and running favorites, plus past ones if requested."""
        from_day = None if include_past else self._clock.today()
        return await self._favorites.list_for(principal.subject, from_day=from_day)


class IsFavorite:
    """Whether the caller marked an event as favorite (detail page)."""

    def __init__(self, favorites: FavoriteRepository) -> None:
        """Create the use case."""
        self._favorites = favorites

    async def __call__(self, principal: Principal, event_id: UUID) -> bool:
        """Return the favorite state."""
        return await self._favorites.is_favorite(principal.subject, event_id)
