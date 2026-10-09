"""Shared list use cases (R13).

Only members may see or change a list (others get 404); all members have the same rights;
only own friends can be added.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Protocol
from uuid import UUID, uuid4

from stadtfest.application.collections.friends import FriendRepository
from stadtfest.application.collections.ports import AccountResolver
from stadtfest.application.events.views import EventSummaryView
from stadtfest.application.shared.errors import InvalidInputError, NotFoundError
from stadtfest.application.shared.ports import Clock
from stadtfest.domain.collections.lists import (
    MEMBERS_MAX,
    NOT_A_FRIEND,
    InvalidListNameError,
    clean_name,
)
from stadtfest.domain.identity.principal import Principal

Now = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ListMemberView:
    """A member as the other members see them."""

    id: UUID
    first_name: str
    last_name: str


@dataclass(frozen=True, slots=True)
class ListEventView:
    """An event of a list with its category."""

    event: EventSummaryView
    category_name: str
    emoji: str
    added_at: datetime


@dataclass(frozen=True, slots=True)
class SharedListView:
    """A list with members and events (chronological, incl. past and cancelled)."""

    id: UUID
    name: str
    members: list[ListMemberView]
    events: list[ListEventView]

    def next_event(self, today: date) -> ListEventView | None:
        """The first event that has not ended."""
        return next((e for e in self.events if e.event.end_date >= today), None)


@dataclass(frozen=True, slots=True)
class SharedListSummary:
    """A list for the overview with its next upcoming event."""

    list: SharedListView
    next_event: ListEventView | None


class SharedListRepository(Protocol):
    """Tables `shared_list`, `list_member`, `list_event`."""

    async def lists_of(self, user_id: UUID) -> list[SharedListView]:
        """All lists the user is a member of, with members and events."""
        ...

    async def get(self, list_id: UUID) -> SharedListView | None:
        """One list, None if unknown."""
        ...

    async def is_member(self, list_id: UUID, user_id: UUID) -> bool:
        """Whether the user is a member of the list."""
        ...

    async def create(
        self, list_id: UUID, name: str, creator: UUID, members: Sequence[UUID], now: datetime
    ) -> None:
        """Create the list with the creator and the members.

        Writes `list.members_added` for the members (not the creator) in the same transaction.
        """
        ...

    async def rename(self, list_id: UUID, name: str) -> None:
        """Set the name."""
        ...

    async def delete(self, list_id: UUID) -> None:
        """Delete the list with its members and events."""
        ...

    async def add_member(self, list_id: UUID, user_id: UUID, by: UUID, now: datetime) -> None:
        """Add the member unless present; a new member writes `list.members_added`."""
        ...

    async def remove_member(self, list_id: UUID, user_id: UUID) -> None:
        """Remove the member; a list without members is deleted in the same transaction."""
        ...

    async def add_event(self, list_id: UUID, event_id: UUID, by: UUID, now: datetime) -> bool:
        """Add a publicly visible event (idempotent); False if it is not visible."""
        ...

    async def remove_event(self, list_id: UUID, event_id: UUID) -> None:
        """Remove the event if present."""
        ...


def _name(name: str) -> str:
    try:
        return clean_name(name)
    except InvalidListNameError:
        raise InvalidInputError({"name": "invalid"}) from None


async def _require_friends(
    friends: FriendRepository, user_id: UUID, candidates: Sequence[UUID]
) -> None:
    """Raises `InvalidInputError(not_a_friend)` unless all candidates are the user's friends."""
    if not candidates:
        return
    own = {friend.id for friend in await friends.friends_of(user_id)}
    if not set(candidates) <= own:
        raise InvalidInputError({"memberIds": NOT_A_FRIEND}, NOT_A_FRIEND)


class _MemberUseCase:
    """Base: resolve the caller and hide lists they are no member of (`404`)."""

    def __init__(self, lists: SharedListRepository, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._lists = lists
        self._accounts = accounts

    async def _member(self, principal: Principal, list_id: UUID) -> UUID:
        user_id = await self._accounts(principal)
        if not await self._lists.is_member(list_id, user_id):
            raise NotFoundError
        return user_id

    async def _view(self, list_id: UUID) -> SharedListView:
        found = await self._lists.get(list_id)
        if found is None:
            raise NotFoundError
        return found


class ListSharedLists:
    """The caller's lists, by the next upcoming event, then by name (R13-US1)."""

    def __init__(
        self, lists: SharedListRepository, accounts: AccountResolver, clock: Clock
    ) -> None:
        """Create the use case."""
        self._lists = lists
        self._accounts = accounts
        self._clock = clock

    async def __call__(self, principal: Principal) -> list[SharedListSummary]:
        """Return the lists with their next event, sorted."""
        today = self._clock.today()
        lists = await self._lists.lists_of(await self._accounts(principal))
        summaries = [SharedListSummary(item, item.next_event(today)) for item in lists]

        def order(item: SharedListSummary) -> tuple[bool, date, str]:
            upcoming = item.next_event
            return (
                upcoming is None,
                upcoming.event.start_date if upcoming else today,
                item.list.name,
            )

        return sorted(summaries, key=order)


class CreateSharedList:
    """Create a list with friends (R13-US2); new members are notified."""

    def __init__(
        self,
        lists: SharedListRepository,
        friends: FriendRepository,
        accounts: AccountResolver,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        self._lists = lists
        self._friends = friends
        self._accounts = accounts
        self._now = now

    async def __call__(
        self, principal: Principal, name: str, member_ids: Sequence[UUID]
    ) -> SharedListView:
        """Create and return the list.

        Raises:
            InvalidInputError: Invalid name, too many members or `not_a_friend`.
        """
        cleaned = _name(name)
        user_id = await self._accounts(principal)
        members = [m for m in dict.fromkeys(member_ids) if m != user_id]
        if len(members) > MEMBERS_MAX:
            raise InvalidInputError({"memberIds": "too_many"})
        await _require_friends(self._friends, user_id, members)
        list_id = uuid4()
        await self._lists.create(list_id, cleaned, user_id, members, self._now())
        created = await self._lists.get(list_id)
        assert created is not None  # noqa: S101  # created just above
        return created


class GetSharedList(_MemberUseCase):
    """A list with members and events (R13-US3)."""

    async def __call__(self, principal: Principal, list_id: UUID) -> SharedListView:
        """Return the list.

        Raises:
            NotFoundError: Unknown list or the caller is no member.
        """
        await self._member(principal, list_id)
        return await self._view(list_id)


class RenameSharedList(_MemberUseCase):
    """Rename a list (any member, R13-US5)."""

    async def __call__(self, principal: Principal, list_id: UUID, name: str) -> SharedListView:
        """Rename and return the list.

        Raises:
            NotFoundError: Unknown list or no member.
            InvalidInputError: Invalid name.
        """
        cleaned = _name(name)
        await self._member(principal, list_id)
        await self._lists.rename(list_id, cleaned)
        return replace(await self._view(list_id), name=cleaned)


class DeleteSharedList(_MemberUseCase):
    """Delete a list for everyone (any member, R13-US5)."""

    async def __call__(self, principal: Principal, list_id: UUID) -> None:
        """Delete it.

        Raises:
            NotFoundError: Unknown list or no member.
        """
        await self._member(principal, list_id)
        await self._lists.delete(list_id)


class AddListMember(_MemberUseCase):
    """Add a friend to a list (idempotent); the new member is notified (R13-US4)."""

    def __init__(
        self,
        lists: SharedListRepository,
        friends: FriendRepository,
        accounts: AccountResolver,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        super().__init__(lists, accounts)
        self._friends = friends
        self._now = now

    async def __call__(self, principal: Principal, list_id: UUID, user_id: UUID) -> None:
        """Add the member.

        Raises:
            NotFoundError: Unknown list or the caller is no member.
            InvalidInputError: `not_a_friend` of the caller.
        """
        caller = await self._member(principal, list_id)
        if user_id == caller:
            return
        await _require_friends(self._friends, caller, [user_id])
        await self._lists.add_member(list_id, user_id, caller, self._now())


class RemoveListMember(_MemberUseCase):
    """Remove a member, or leave with the own ID; the last one out deletes the list."""

    async def __call__(self, principal: Principal, list_id: UUID, user_id: UUID) -> None:
        """Remove the membership (idempotent).

        Raises:
            NotFoundError: Unknown list or the caller is no member.
        """
        await self._member(principal, list_id)
        await self._lists.remove_member(list_id, user_id)


class AddListEvent(_MemberUseCase):
    """Add a publicly visible event to a list (idempotent, R13-US4)."""

    def __init__(
        self, lists: SharedListRepository, accounts: AccountResolver, now: Now = _utc_now
    ) -> None:
        """Create the use case."""
        super().__init__(lists, accounts)
        self._now = now

    async def __call__(self, principal: Principal, list_id: UUID, event_id: UUID) -> None:
        """Add the event.

        Raises:
            NotFoundError: Unknown list, no member, or the event is not public.
        """
        caller = await self._member(principal, list_id)
        if not await self._lists.add_event(list_id, event_id, caller, self._now()):
            raise NotFoundError


class RemoveListEvent(_MemberUseCase):
    """Remove an event from a list (idempotent)."""

    async def __call__(self, principal: Principal, list_id: UUID, event_id: UUID) -> None:
        """Remove it.

        Raises:
            NotFoundError: Unknown list or no member.
        """
        await self._member(principal, list_id)
        await self._lists.remove_event(list_id, event_id)
