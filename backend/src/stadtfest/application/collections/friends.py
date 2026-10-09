"""Friend use cases (R12): own link, look up and accept a link, list and remove friends."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from stadtfest.application.collections.ports import AccountResolver
from stadtfest.application.shared.errors import (
    InvalidInputError,
    NotFoundError,
    TooManyRequestsError,
)
from stadtfest.application.shared.ports import RateLimiter
from stadtfest.domain.collections.friends import (
    LOOKUP_LIMIT,
    LOOKUP_WINDOW_SECONDS,
    LinkOwner,
    is_token,
    new_token,
)
from stadtfest.domain.identity.principal import Principal

SELF_LINK = "self_link"
RATE_LIMITED = "rate_limited"

Now = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class FriendLinkView:
    """The caller's link token."""

    token: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LinkTarget:
    """Owner of a token as stored."""

    user_id: UUID
    first_name: str
    last_name: str


@dataclass(frozen=True, slots=True)
class FriendView:
    """A friend in the list."""

    id: UUID
    first_name: str
    last_name: str
    since: datetime


class FriendRepository(Protocol):
    """Tables `friend_link` and `friendship`."""

    async def link_of(self, user_id: UUID) -> FriendLinkView | None:
        """The user's current link, None if there is none yet."""
        ...

    async def set_link(self, user_id: UUID, token: str, now: datetime) -> FriendLinkView:
        """Store a new token for the user, replacing an older one."""
        ...

    async def owner_of(self, token: str) -> LinkTarget | None:
        """The owner of a current token."""
        ...

    async def befriend(self, owner_id: UUID, friend_id: UUID, now: datetime) -> FriendView:
        """Create the friendship in both directions unless it exists.

        A new friendship writes `friendship.created` to the outbox in the same transaction.

        Returns:
            The owner as seen by the friend.
        """
        ...

    async def friends_of(self, user_id: UUID) -> list[FriendView]:
        """Friends ordered by first and last name."""
        ...

    async def remove(self, user_id: UUID, friend_id: UUID) -> None:
        """Delete both directions; no-op if they are no friends."""
        ...


class GetFriendLink:
    """The caller's friend link; created on first use (R12-US1)."""

    def __init__(
        self, friends: FriendRepository, accounts: AccountResolver, now: Now = _utc_now
    ) -> None:
        """Create the use case."""
        self._friends = friends
        self._accounts = accounts
        self._now = now

    async def __call__(self, principal: Principal) -> FriendLinkView:
        """Return the existing link or create one."""
        user_id = await self._accounts(principal)
        link = await self._friends.link_of(user_id)
        return link or await self._friends.set_link(user_id, new_token(), self._now())


class RotateFriendLink:
    """Reset the link: a new token, the old one stops working at once."""

    def __init__(
        self, friends: FriendRepository, accounts: AccountResolver, now: Now = _utc_now
    ) -> None:
        """Create the use case."""
        self._friends = friends
        self._accounts = accounts
        self._now = now

    async def __call__(self, principal: Principal) -> FriendLinkView:
        """Store and return a new token."""
        user_id = await self._accounts(principal)
        return await self._friends.set_link(user_id, new_token(), self._now())


async def _resolve(
    friends: FriendRepository, limiter: RateLimiter, user_id: UUID, token: str
) -> LinkTarget:
    """The owner of a token, counting the attempt against the guessing limit.

    Raises:
        TooManyRequestsError: More than 20 attempts in the last hour.
        NotFoundError: Unknown, malformed or reset token.
        InvalidInputError: `self_link` for the caller's own link.
    """
    if not await limiter.hit(f"friend-link:{user_id}", LOOKUP_LIMIT, LOOKUP_WINDOW_SECONDS):
        raise TooManyRequestsError(RATE_LIMITED)
    target = await friends.owner_of(token) if is_token(token) else None
    if target is None:
        raise NotFoundError
    if target.user_id == user_id:
        raise InvalidInputError({"token": SELF_LINK}, SELF_LINK)
    return target


class LookUpFriendLink:
    """Who shared a link: first name and initial only, for signed-in users (R12-US2)."""

    def __init__(
        self, friends: FriendRepository, accounts: AccountResolver, limiter: RateLimiter
    ) -> None:
        """Create the use case."""
        self._friends = friends
        self._accounts = accounts
        self._limiter = limiter

    async def __call__(self, principal: Principal, token: str) -> LinkOwner:
        """Return the owner.

        Raises:
            TooManyRequestsError, NotFoundError, InvalidInputError: See `_resolve`.
        """
        user_id = await self._accounts(principal)
        target = await _resolve(self._friends, self._limiter, user_id, token)
        return LinkOwner.of(target.first_name, target.last_name)


class AcceptFriendLink:
    """Become friends with the link owner (idempotent); the owner is notified."""

    def __init__(
        self,
        friends: FriendRepository,
        accounts: AccountResolver,
        limiter: RateLimiter,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        self._friends = friends
        self._accounts = accounts
        self._limiter = limiter
        self._now = now

    async def __call__(self, principal: Principal, token: str) -> FriendView:
        """Create the friendship and return the new friend.

        Raises:
            TooManyRequestsError, NotFoundError, InvalidInputError: See `_resolve`.
        """
        user_id = await self._accounts(principal)
        target = await _resolve(self._friends, self._limiter, user_id, token)
        return await self._friends.befriend(target.user_id, user_id, self._now())


class ListFriends:
    """The caller's friends (R12-US3)."""

    def __init__(self, friends: FriendRepository, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._friends = friends
        self._accounts = accounts

    async def __call__(self, principal: Principal) -> list[FriendView]:
        """Return the friends, alphabetically."""
        return await self._friends.friends_of(await self._accounts(principal))


class RemoveFriend:
    """End a friendship in both directions, without a notification (idempotent)."""

    def __init__(self, friends: FriendRepository, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._friends = friends
        self._accounts = accounts

    async def __call__(self, principal: Principal, friend_id: UUID) -> None:
        """Remove the friendship."""
        await self._friends.remove(await self._accounts(principal), friend_id)
