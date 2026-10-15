"""Invitation use cases (R14): invite friends to an event, answer, remind, invitation link.

The host sees the own invitation with all invitees; invitees see the invitation they
received. Everyone else gets `404`. The message is user free text: it is never logged.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from stadtfest.application.collections.friends import (
    RATE_LIMITED,
    SELF_LINK,
    FriendRepository,
)
from stadtfest.application.collections.lists import require_friends
from stadtfest.application.collections.ports import AccountResolver
from stadtfest.application.events.views import EventSummaryView
from stadtfest.application.shared.errors import (
    InvalidInputError,
    NotFoundError,
    TooManyRequestsError,
)
from stadtfest.application.shared.ports import Clock, RateLimiter
from stadtfest.domain.collections.friends import (
    LOOKUP_LIMIT,
    LOOKUP_WINDOW_SECONDS,
    LinkOwner,
    is_token,
    new_token,
)
from stadtfest.domain.collections.invitations import (
    EVENT_NOT_INVITABLE,
    INVITEES_MAX,
    RETENTION,
    InviteeStatus,
    clean_message,
    is_invitable,
    reminder_wait,
)
from stadtfest.domain.identity.principal import Principal

REMINDED_RECENTLY = "reminded_recently"

Now = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class InvitationPersonView:
    """Host or invitee as the others see them."""

    id: UUID
    first_name: str
    last_name: str


@dataclass(frozen=True, slots=True)
class InviteeView:
    """An invitee with the answer."""

    person: InvitationPersonView
    status: InviteeStatus
    invited_at: datetime
    responded_at: datetime | None


@dataclass(frozen=True, slots=True)
class InvitationView:
    """An invitation with its event, host and invitees (by invitation time)."""

    id: UUID
    event: EventSummaryView
    host: InvitationPersonView
    message: str | None
    created_at: datetime
    last_reminder_at: datetime | None
    invitees: list[InviteeView]

    def invitee(self, user_id: UUID) -> InviteeView | None:
        """The user's invitee entry, None if not invited."""
        return next((i for i in self.invitees if i.person.id == user_id), None)

    def accepted(self) -> list[InvitationPersonView]:
        """Invitees who accepted."""
        return [i.person for i in self.invitees if i.status is InviteeStatus.ACCEPTED]


@dataclass(frozen=True, slots=True)
class ReceivedInvitationView:
    """An invitation as the invitee sees it: own status and the others."""

    invitation: InvitationView
    status: InviteeStatus
    others: list[InviteeView]

    @classmethod
    def of(cls, invitation: InvitationView, user_id: UUID) -> ReceivedInvitationView:
        """Split the invitees into the caller and the others."""
        own = invitation.invitee(user_id)
        assert own is not None  # noqa: S101  # callers checked the membership
        others = [i for i in invitation.invitees if i.person.id != user_id]
        return cls(invitation, own.status, others)


class SummaryRole(StrEnum):
    """Perspective of the "… kommen mit" hint."""

    HOST = "host"
    GUEST = "guest"


@dataclass(frozen=True, slots=True)
class InvitationSummaryView:
    """Who comes along to an event (R14-US6)."""

    invitation_id: UUID
    role: SummaryRole
    people: list[InvitationPersonView]


@dataclass(frozen=True, slots=True)
class InvitationLinkPreviewView:
    """Host (first name + initial) and event of a link."""

    host: LinkOwner
    event: EventSummaryView
    own: bool


class InvitationRepository(Protocol):
    """Tables `invitation` and `invitee`; domain events go into the outbox."""

    async def event(self, event_id: UUID) -> EventSummaryView | None:
        """The publicly visible (published or cancelled), not deleted event."""
        ...

    async def get(self, invitation_id: UUID) -> InvitationView | None:
        """One invitation."""
        ...

    async def of_host(self, event_id: UUID, host_id: UUID) -> InvitationView | None:
        """The host's invitation to the event."""
        ...

    async def accepted_for(self, event_id: UUID, user_id: UUID) -> InvitationView | None:
        """The oldest invitation to the event that the user accepted."""
        ...

    async def received_by(self, user_id: UUID) -> list[InvitationView]:
        """Invitations the user received, newest first."""
        ...

    async def by_token(self, token: str) -> InvitationView | None:
        """The invitation with this link token."""
        ...

    async def invite(
        self,
        event_id: UUID,
        host_id: UUID,
        user_ids: Sequence[UUID],
        message: str | None,
        now: datetime,
    ) -> UUID:
        """Create the invitation if needed and add the users once.

        Sets the message only if given. New invitees write `invitation.invitees_added`
        in the same transaction.

        Returns:
            The invitation ID.
        """
        ...

    async def link_token(self, event_id: UUID, host_id: UUID, token: str, now: datetime) -> str:
        """Create the invitation if needed; store `token` unless one exists; return the token."""
        ...

    async def remind(self, invitation_id: UUID, now: datetime) -> int:
        """Set `last_reminder_at` and write `invitation.reminded` for the open invitees.

        Returns:
            Number of open invitees (no event if 0).
        """
        ...

    async def respond(
        self, invitation_id: UUID, user_id: UUID, status: InviteeStatus, now: datetime
    ) -> None:
        """Store the answer.

        `accepted` also adds the favorite. A changed answer other than `open` writes
        `invitation.responded`, all in one transaction.
        """
        ...

    async def join(self, invitation_id: UUID, user_id: UUID, now: datetime) -> None:
        """Add the user as open invitee unless present (link accepted)."""
        ...

    async def purge(self, ended_before: datetime) -> int:
        """Delete invitations to events that ended before the given time; return the count."""
        ...


def _require_invitable(event: EventSummaryView, clock: Clock) -> None:
    if not is_invitable(event.status, event.end_date, clock.today()):
        raise InvalidInputError({"eventId": EVENT_NOT_INVITABLE}, EVENT_NOT_INVITABLE)


async def _invitable_event(
    invitations: InvitationRepository, event_id: UUID, clock: Clock
) -> EventSummaryView:
    event = await invitations.event(event_id)
    if event is None:
        raise NotFoundError
    _require_invitable(event, clock)
    return event


async def _received(
    invitations: InvitationRepository, invitation_id: UUID, user_id: UUID
) -> InvitationView:
    """The invitation if the user is an invitee, otherwise `NotFoundError`."""
    found = await invitations.get(invitation_id)
    if found is None or found.invitee(user_id) is None:
        raise NotFoundError
    return found


class GetHostInvitation:
    """The caller's own invitation to an event (R14-US1)."""

    def __init__(self, invitations: InvitationRepository, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._accounts = accounts

    async def __call__(self, principal: Principal, event_id: UUID) -> InvitationView:
        """Return it.

        Raises:
            NotFoundError: The caller has not invited anyone to the event yet.
        """
        found = await self._invitations.of_host(event_id, await self._accounts(principal))
        if found is None:
            raise NotFoundError
        return found


class InviteFriends:
    """Invite friends to an event (R14-US2); every new invitee gets `invite`."""

    def __init__(
        self,
        invitations: InvitationRepository,
        friends: FriendRepository,
        accounts: AccountResolver,
        clock: Clock,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._friends = friends
        self._accounts = accounts
        self._clock = clock
        self._now = now

    async def __call__(
        self,
        principal: Principal,
        event_id: UUID,
        user_ids: Sequence[UUID],
        message: str | None,
    ) -> InvitationView:
        """Invite and return the invitation.

        Raises:
            NotFoundError: Unknown or not public event.
            InvalidInputError: `event_not_invitable`, `not_a_friend`, too long message or
                too many users.
        """
        try:
            cleaned = clean_message(message)
        except ValueError:
            raise InvalidInputError({"message": "too_long"}) from None
        host = await self._accounts(principal)
        users = [u for u in dict.fromkeys(user_ids) if u != host]
        if len(users) > INVITEES_MAX:
            raise InvalidInputError({"userIds": "too_many"})
        await _invitable_event(self._invitations, event_id, self._clock)
        await require_friends(self._friends, host, users, "userIds")
        invitation_id = await self._invitations.invite(event_id, host, users, cleaned, self._now())
        created = await self._invitations.get(invitation_id)
        assert created is not None  # noqa: S101  # written just above
        return created


class CreateInvitationLink:
    """The link token of the caller's invitation, for friends without the app (R14-US3)."""

    def __init__(
        self,
        invitations: InvitationRepository,
        accounts: AccountResolver,
        clock: Clock,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._accounts = accounts
        self._clock = clock
        self._now = now

    async def __call__(self, principal: Principal, event_id: UUID) -> str:
        """Return the token (created on first use).

        Raises:
            NotFoundError: Unknown event.
            InvalidInputError: `event_not_invitable`.
        """
        host = await self._accounts(principal)
        await _invitable_event(self._invitations, event_id, self._clock)
        return await self._invitations.link_token(event_id, host, new_token(), self._now())


class RemindInvitees:
    """Remind open invitees, at most once per 24 hours (R14-US4)."""

    def __init__(
        self, invitations: InvitationRepository, accounts: AccountResolver, now: Now = _utc_now
    ) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._accounts = accounts
        self._now = now

    async def __call__(self, principal: Principal, invitation_id: UUID) -> int:
        """Remind and return how many invitees were reminded.

        Raises:
            NotFoundError: Unknown invitation or the caller is not the host.
            TooManyRequestsError: `reminded_recently` with `retryAfter` in seconds.
        """
        host = await self._accounts(principal)
        found = await self._invitations.get(invitation_id)
        if found is None or found.host.id != host:
            raise NotFoundError
        now = self._now()
        wait = reminder_wait(found.last_reminder_at, now)
        if wait is not None:
            retry = str(int(wait.total_seconds()) + 1)
            raise TooManyRequestsError(REMINDED_RECENTLY, {"retryAfter": retry})
        if not any(i.status is InviteeStatus.OPEN for i in found.invitees):
            return 0
        return await self._invitations.remind(invitation_id, now)


class RespondToInvitation:
    """Accept, decline or reset an invitation (R14-US5)."""

    def __init__(
        self,
        invitations: InvitationRepository,
        accounts: AccountResolver,
        clock: Clock,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._accounts = accounts
        self._clock = clock
        self._now = now

    async def __call__(
        self, principal: Principal, invitation_id: UUID, status: InviteeStatus
    ) -> ReceivedInvitationView:
        """Store the answer and return the invitation.

        Raises:
            NotFoundError: Unknown invitation or the caller is not invited.
            InvalidInputError: `event_not_invitable` (ended or cancelled).
        """
        user_id = await self._accounts(principal)
        found = await _received(self._invitations, invitation_id, user_id)
        _require_invitable(found.event, self._clock)
        await self._invitations.respond(invitation_id, user_id, status, self._now())
        updated = await self._invitations.get(invitation_id)
        assert updated is not None  # noqa: S101  # cascades only with the event
        return ReceivedInvitationView.of(updated, user_id)


class ListReceivedInvitations:
    """Invitations the caller received, newest first."""

    def __init__(self, invitations: InvitationRepository, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._accounts = accounts

    async def __call__(self, principal: Principal) -> list[ReceivedInvitationView]:
        """Return them."""
        user_id = await self._accounts(principal)
        return [
            ReceivedInvitationView.of(item, user_id)
            for item in await self._invitations.received_by(user_id)
        ]


class GetReceivedInvitation:
    """A received invitation (invitees only, R14-US5)."""

    def __init__(self, invitations: InvitationRepository, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._accounts = accounts

    async def __call__(self, principal: Principal, invitation_id: UUID) -> ReceivedInvitationView:
        """Return it.

        Raises:
            NotFoundError: Unknown invitation or the caller is not invited.
        """
        user_id = await self._accounts(principal)
        found = await _received(self._invitations, invitation_id, user_id)
        return ReceivedInvitationView.of(found, user_id)


async def _by_token(
    invitations: InvitationRepository, limiter: RateLimiter, user_id: UUID, token: str
) -> InvitationView:
    """The invitation of a link; attempts count against the friend link limit.

    Raises:
        TooManyRequestsError: More than 20 attempts in the last hour.
        NotFoundError: Unknown or malformed token.
    """
    if not await limiter.hit(f"friend-link:{user_id}", LOOKUP_LIMIT, LOOKUP_WINDOW_SECONDS):
        raise TooManyRequestsError(RATE_LIMITED)
    found = await invitations.by_token(token) if is_token(token) else None
    if found is None:
        raise NotFoundError
    return found


class LookUpInvitationLink:
    """Preview of an invitation link for signed-in users (R14-US3)."""

    def __init__(
        self,
        invitations: InvitationRepository,
        accounts: AccountResolver,
        limiter: RateLimiter,
    ) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._accounts = accounts
        self._limiter = limiter

    async def __call__(self, principal: Principal, token: str) -> InvitationLinkPreviewView:
        """Return host and event.

        Raises:
            TooManyRequestsError, NotFoundError: See `_by_token`.
        """
        user_id = await self._accounts(principal)
        found = await _by_token(self._invitations, self._limiter, user_id, token)
        host = LinkOwner.of(found.host.first_name, found.host.last_name)
        return InvitationLinkPreviewView(host, found.event, found.host.id == user_id)


class AcceptInvitationLink:
    """Accept a link: befriend the host and become an open invitee (idempotent)."""

    def __init__(
        self,
        invitations: InvitationRepository,
        friends: FriendRepository,
        accounts: AccountResolver,
        limiter: RateLimiter,
        clock: Clock,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._friends = friends
        self._accounts = accounts
        self._limiter = limiter
        self._clock = clock
        self._now = now

    async def __call__(self, principal: Principal, token: str) -> ReceivedInvitationView:
        """Accept and return the received invitation.

        Raises:
            TooManyRequestsError, NotFoundError: See `_by_token`.
            InvalidInputError: `self_link` or `event_not_invitable`.
        """
        user_id = await self._accounts(principal)
        found = await _by_token(self._invitations, self._limiter, user_id, token)
        if found.host.id == user_id:
            raise InvalidInputError({"token": SELF_LINK}, SELF_LINK)
        _require_invitable(found.event, self._clock)
        now = self._now()
        await self._friends.befriend(found.host.id, user_id, now)
        await self._invitations.join(found.id, user_id, now)
        joined = await self._invitations.get(found.id)
        assert joined is not None  # noqa: S101  # cascades only with the event
        return ReceivedInvitationView.of(joined, user_id)


class GetInvitationSummary:
    """Who comes along, for the event detail (R14-US6)."""

    def __init__(self, invitations: InvitationRepository, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._accounts = accounts

    async def __call__(self, principal: Principal, event_id: UUID) -> InvitationSummaryView | None:
        """As host the accepted invitees, as accepted invitee the host and the others.

        None if the caller is neither or nobody comes along.
        """
        user_id = await self._accounts(principal)
        hosted = await self._invitations.of_host(event_id, user_id)
        if hosted is not None and hosted.accepted():
            return InvitationSummaryView(hosted.id, SummaryRole.HOST, hosted.accepted())
        guest = await self._invitations.accepted_for(event_id, user_id)
        if guest is None:
            return None
        people = [guest.host, *(p for p in guest.accepted() if p.id != user_id)]
        return InvitationSummaryView(guest.id, SummaryRole.GUEST, people)


class PurgeInvitations:
    """Delete invitations six months after the event ended (daily job, Löschkonzept)."""

    def __init__(self, invitations: InvitationRepository, now: Now = _utc_now) -> None:
        """Create the use case."""
        self._invitations = invitations
        self._now = now

    async def __call__(self) -> int:
        """Delete and return the count."""
        return await self._invitations.purge(self._now() - RETENTION)
