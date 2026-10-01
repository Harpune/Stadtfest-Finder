"""Outbound ports of the collections context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from stadtfest.application.events.views import EventSummaryView
from stadtfest.domain.identity.principal import Principal


@dataclass(frozen=True, slots=True)
class FavoriteView:
    """A favorite with its event, as shown in the timeline."""

    event: EventSummaryView
    category_name: str
    emoji: str
    favorited_at: datetime


class FavoriteRepository(Protocol):
    """Favorites of users, keyed by the IdP subject of the user."""

    async def add(self, subject: str, event_id: UUID) -> bool:
        """Mark a publicly visible event as favorite and count it once.

        Returns:
            False if the event is not publicly visible (draft, deleted, unknown).
        """
        ...

    async def remove(self, subject: str, event_id: UUID) -> None:
        """Remove the favorite if present and adjust the event's counter."""
        ...

    async def list_for(self, subject: str, *, from_day: date | None) -> list[FavoriteView]:
        """Favorites of publicly visible events, ordered by start date.

        Args:
            subject: IdP subject of the user.
            from_day: Leave out events that ended before this day; None returns all.
        """
        ...

    async def is_favorite(self, subject: str, event_id: UUID) -> bool:
        """Return True if the user marked the event as favorite."""
        ...


class AccountResolver(Protocol):
    """Makes sure the caller has an account (identity context) and returns its ID."""

    async def __call__(self, principal: Principal) -> UUID:
        """Create the account on first use and return the user ID."""
        ...
