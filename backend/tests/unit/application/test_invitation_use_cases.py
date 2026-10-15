"""Invitation use cases with fake adapters (R14)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, date, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest

from stadtfest.application.collections.invitations import (
    AcceptInvitationLink,
    CreateInvitationLink,
    GetHostInvitation,
    GetInvitationSummary,
    GetReceivedInvitation,
    InviteFriends,
    ListReceivedInvitations,
    LookUpInvitationLink,
    PurgeInvitations,
    RemindInvitees,
    RespondToInvitation,
    SummaryRole,
)
from stadtfest.application.events.views import EventSummaryView
from stadtfest.application.shared.errors import (
    InvalidInputError,
    NotFoundError,
    TooManyRequestsError,
)
from stadtfest.domain.collections.invitations import InvitationEventType, InviteeStatus
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import (
    FakeAccountResolver,
    FakeFriendRepository,
    FakeInvitationRepository,
    FakeRateLimiter,
    FixedClock,
)

LENA, TIM, MIA, JO = (
    Principal(f"sub-{n}", frozenset({Role.USER})) for n in ("lena", "tim", "mia", "jo")
)
LENA_ID, TIM_ID, MIA_ID, JO_ID = (uuid5(NAMESPACE_URL, p.subject) for p in (LENA, TIM, MIA, JO))
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
TODAY = date(2026, 10, 9)


def _event(
    end: date = date(2026, 12, 22), status: EventStatus = EventStatus.PUBLISHED
) -> EventSummaryView:
    return EventSummaryView(
        id=uuid4(),
        name="Ulmer Weihnachtsmarkt",
        short_name="Weihnachtsmarkt",
        status=status,
        start_date=date(2026, 11, 23),
        end_date=end,
        place="Münsterplatz",
        city="Ulm",
        location=GeoPoint(48.4, 10.0),
        category_id=uuid4(),
    )


class Setup:
    def __init__(self) -> None:
        self.event = _event()
        people = {
            LENA_ID: ("Lena", "Berg"),
            TIM_ID: ("Tim", "Kurz"),
            MIA_ID: ("Mia", "Sommer"),
            JO_ID: ("Jo", "Weit"),
        }
        self.invitations = FakeInvitationRepository(
            public_events={self.event.id: self.event}, people=people
        )
        self.friends = FakeFriendRepository(people=people)
        for friend in (TIM_ID, MIA_ID):  # Jo is no friend of Lena
            self.friends.friendships[frozenset({LENA_ID, friend})] = NOW
        self.accounts = FakeAccountResolver()
        self.clock = FixedClock(TODAY)
        self.limiter = FakeRateLimiter()
        self.now = NOW

    def invite(self) -> InviteFriends:
        return InviteFriends(
            self.invitations, self.friends, self.accounts, self.clock, lambda: self.now
        )

    def respond(self) -> RespondToInvitation:
        return RespondToInvitation(self.invitations, self.accounts, self.clock, lambda: self.now)

    def remind(self) -> RemindInvitees:
        return RemindInvitees(self.invitations, self.accounts, lambda: self.now)

    async def invited(self, *users: UUID, message: str | None = None) -> UUID:
        return (await self.invite()(LENA, self.event.id, list(users), message)).id


@pytest.fixture
def s() -> Setup:
    return Setup()


async def test_invite_creates_one_invitation_and_notifies_only_new_invitees(s: Setup) -> None:
    first = await s.invite()(LENA, s.event.id, [TIM_ID, LENA_ID], "  Kommt mit!  ")
    second = await s.invite()(LENA, s.event.id, [TIM_ID, MIA_ID], None)

    assert first.id == second.id
    assert [i.person.id for i in second.invitees] == [TIM_ID, MIA_ID]
    assert second.message == "Kommt mit!"  # kept, because no new message was set
    added = [p["userIds"] for t, p in s.invitations.events_written]
    assert added == [[TIM_ID], [MIA_ID]]


async def test_only_friends_can_be_invited(s: Setup) -> None:
    with pytest.raises(InvalidInputError) as raised:
        await s.invite()(LENA, s.event.id, [TIM_ID, JO_ID], None)
    assert raised.value.code == "not_a_friend"
    assert raised.value.fields == {"userIds": "not_a_friend"}
    assert s.invitations.rows == {}


@pytest.mark.parametrize(
    "event",
    [_event(end=date(2026, 10, 8)), _event(status=EventStatus.CANCELLED)],
    ids=["past", "cancelled"],
)
async def test_past_and_cancelled_events_are_not_invitable(
    s: Setup, event: EventSummaryView
) -> None:
    s.invitations.public_events[event.id] = event
    with pytest.raises(InvalidInputError) as raised:
        await s.invite()(LENA, event.id, [TIM_ID], None)
    assert raised.value.code == "event_not_invitable"
    link = CreateInvitationLink(s.invitations, s.accounts, s.clock)
    with pytest.raises(InvalidInputError):
        await link(LENA, event.id)


async def test_unknown_event_and_too_long_message(s: Setup) -> None:
    with pytest.raises(NotFoundError):
        await s.invite()(LENA, uuid4(), [TIM_ID], None)
    with pytest.raises(InvalidInputError):
        await s.invite()(LENA, s.event.id, [TIM_ID], "x" * 281)


async def test_host_invitation_is_404_before_inviting(s: Setup) -> None:
    get = GetHostInvitation(s.invitations, s.accounts)
    with pytest.raises(NotFoundError):
        await get(LENA, s.event.id)
    await s.invited(TIM_ID)
    assert (await get(LENA, s.event.id)).host.id == LENA_ID


async def test_accept_sets_favorite_and_notifies_host_decline_keeps_it(s: Setup) -> None:
    invitation = await s.invited(TIM_ID)

    accepted = await s.respond()(TIM, invitation, InviteeStatus.ACCEPTED)
    assert accepted.status is InviteeStatus.ACCEPTED
    assert (TIM_ID, s.event.id) in s.invitations.favorites
    declined = await s.respond()(TIM, invitation, InviteeStatus.DECLINED)
    assert declined.status is InviteeStatus.DECLINED
    assert (TIM_ID, s.event.id) in s.invitations.favorites  # favorite stays
    reset = await s.respond()(TIM, invitation, InviteeStatus.OPEN)
    assert reset.status is InviteeStatus.OPEN

    responded = [
        p["status"]
        for t, p in s.invitations.events_written
        if t == InvitationEventType.RESPONDED.value
    ]
    assert responded == ["accepted", "declined"]  # `open` notifies nobody


async def test_only_invitees_can_see_and_answer(s: Setup) -> None:
    invitation = await s.invited(TIM_ID)
    with pytest.raises(NotFoundError):
        await s.respond()(MIA, invitation, InviteeStatus.ACCEPTED)
    with pytest.raises(NotFoundError):
        await GetReceivedInvitation(s.invitations, s.accounts)(LENA, invitation)
    received = await GetReceivedInvitation(s.invitations, s.accounts)(TIM, invitation)
    assert received.invitation.host.first_name == "Lena"
    assert received.others == []


async def test_answer_is_not_possible_after_the_event(s: Setup) -> None:
    invitation = await s.invited(TIM_ID)
    s.clock = FixedClock(date(2026, 12, 23))
    with pytest.raises(InvalidInputError):
        await s.respond()(TIM, invitation, InviteeStatus.ACCEPTED)


async def test_reminder_reaches_open_invitees_once_per_day(s: Setup) -> None:
    invitation = await s.invited(TIM_ID, MIA_ID)
    await s.respond()(TIM, invitation, InviteeStatus.ACCEPTED)

    assert await s.remind()(LENA, invitation) == 1
    s.now = NOW + timedelta(hours=23)
    with pytest.raises(TooManyRequestsError) as raised:
        await s.remind()(LENA, invitation)
    assert raised.value.code == "reminded_recently"
    assert raised.value.fields == {"retryAfter": "3601"}
    s.now = NOW + timedelta(hours=24)
    assert await s.remind()(LENA, invitation) == 1
    with pytest.raises(NotFoundError):
        await s.remind()(TIM, invitation)  # not the host


async def test_reminder_without_open_invitees_does_nothing(s: Setup) -> None:
    invitation = await s.invited(TIM_ID)
    await s.respond()(TIM, invitation, InviteeStatus.DECLINED)
    assert await s.remind()(LENA, invitation) == 0
    assert s.invitations.rows[invitation].last_reminder_at is None


async def test_link_accept_befriends_host_and_joins_as_open(s: Setup) -> None:
    token = await CreateInvitationLink(s.invitations, s.accounts, s.clock)(LENA, s.event.id)
    assert token == await CreateInvitationLink(s.invitations, s.accounts, s.clock)(LENA, s.event.id)
    preview = await LookUpInvitationLink(s.invitations, s.accounts, s.limiter)(JO, token)
    assert (preview.host.first_name, preview.host.last_name_initial, preview.own) == (
        "Lena",
        "B",
        False,
    )
    assert (await LookUpInvitationLink(s.invitations, s.accounts, s.limiter)(LENA, token)).own

    accept = AcceptInvitationLink(s.invitations, s.friends, s.accounts, s.limiter, s.clock)
    received = await accept(JO, token)
    assert received.status is InviteeStatus.OPEN
    assert frozenset({LENA_ID, JO_ID}) in s.friends.friendships
    assert (await accept(JO, token)).invitation.id == received.invitation.id  # idempotent
    with pytest.raises(InvalidInputError) as raised:
        await accept(LENA, token)
    assert raised.value.code == "self_link"
    with pytest.raises(NotFoundError):
        await accept(JO, "x" * 22)


async def test_link_lookups_are_rate_limited(s: Setup) -> None:
    look_up = LookUpInvitationLink(s.invitations, s.accounts, s.limiter)
    for _ in range(20):
        with pytest.raises(NotFoundError):
            await look_up(JO, "A" * 22)
    with pytest.raises(TooManyRequestsError):
        await look_up(JO, "A" * 22)


async def test_summary_per_role(s: Setup) -> None:
    summary = GetInvitationSummary(s.invitations, s.accounts)
    invitation = await s.invited(TIM_ID, MIA_ID)
    assert await summary(LENA, s.event.id) is None  # nobody accepted yet
    await s.respond()(TIM, invitation, InviteeStatus.ACCEPTED)
    await s.respond()(MIA, invitation, InviteeStatus.ACCEPTED)

    host = await summary(LENA, s.event.id)
    assert host is not None
    assert host.role is SummaryRole.HOST
    assert [p.id for p in host.people] == [TIM_ID, MIA_ID]
    guest = await summary(TIM, s.event.id)
    assert guest is not None
    assert guest.role is SummaryRole.GUEST
    assert [p.id for p in guest.people] == [LENA_ID, MIA_ID]
    assert await summary(JO, s.event.id) is None


async def test_received_list_and_purge(s: Setup) -> None:
    invitation = await s.invited(TIM_ID)
    received = await ListReceivedInvitations(s.invitations, s.accounts)(TIM)
    assert [r.invitation.id for r in received] == [invitation]

    purge = PurgeInvitations(s.invitations, lambda: datetime(2027, 6, 22, tzinfo=UTC))
    assert await purge() == 0
    ended = dataclasses.replace(s.event, end_date=date(2026, 12, 20))
    s.invitations.public_events[s.event.id] = ended
    assert await purge() == 1
