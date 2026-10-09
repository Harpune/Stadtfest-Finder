from collections.abc import Mapping
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from stadtfest.application.moderation.use_cases import (
    CancelModEvent,
    CreateModEvent,
    DeleteModEvent,
    GetModEvent,
    ListModEvents,
    ModStatus,
    PublishModEvent,
    UnpublishModEvent,
    UpdateModEvent,
)
from stadtfest.application.outbox.ports import OutboxMessage
from stadtfest.application.outbox.use_cases import HandleDomainEvent, PurgeOutbox, RelayOutbox
from stadtfest.application.shared.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
)
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.maintenance import (
    DomainEventType,
    EventContent,
    ManagedEvent,
)
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import (
    FakeAccountResolver,
    FakeActiveCategories,
    FakeCache,
    FakeEventFavorites,
    FakeEventQueue,
    FakeManagedEventRepository,
    FakeOutboxStore,
    FixedClock,
)

TODAY = date(2026, 10, 1)
CATEGORY = uuid4()
MODERATOR = Principal("sub-mod", frozenset({Role.USER, Role.MODERATOR}))
USER = Principal("sub-user", frozenset({Role.USER}))
COMPLETE = {
    "category_id": CATEGORY,
    "start_date": date(2026, 10, 17),
    "end_date": date(2026, 10, 18),
    "place": "Festplatz",
    "address": "Wasseralfingen",
    "city": "Aalen",
    "postal_code": "73430",
    "lat": 48.86,
    "lon": 10.1,
}


class Setup:
    def __init__(self) -> None:
        self.events = FakeManagedEventRepository()
        clock = FixedClock(TODAY)
        accounts = FakeAccountResolver()
        base = (self.events, clock)
        self.list = ListModEvents(*base)
        self.get = GetModEvent(*base)
        self.create = CreateModEvent(*base, accounts)
        self.update = UpdateModEvent(*base, accounts)
        self.publish = PublishModEvent(
            *base,
            accounts,
            FakeActiveCategories(frozenset({CATEGORY})),
            now=lambda: datetime(2026, 10, 1, 12, tzinfo=UTC),
        )
        self.unpublish = UnpublishModEvent(*base, accounts)
        self.cancel = CancelModEvent(*base, accounts)
        self.delete = DeleteModEvent(*base, accounts)

    def stored(
        self,
        status: EventStatus,
        name: str = "Fest",
        **content: object,
    ) -> ManagedEvent:
        event = ManagedEvent(
            uuid4(),
            status,
            EventContent(name=name, **(COMPLETE | content)).with_defaults(),  # type: ignore[arg-type]
        )
        self.events.events[event.id] = event
        return event


@pytest.fixture
def s() -> Setup:
    return Setup()


async def _ignore(*_args: object) -> None:
    return None


def _handler(cache: FakeCache, favorites: FakeEventFavorites) -> HandleDomainEvent:
    return HandleDomainEvent(cache, favorites, _ignore, _ignore)


def _types(s: Setup) -> list[DomainEventType]:
    return [e.type for e in s.events.outbox]


# --- authorization (R07-US6) -----------------------------------------------------------


async def test_non_moderators_are_forbidden(s: Setup) -> None:
    with pytest.raises(ForbiddenError):
        await s.list(USER)


async def test_every_moderator_maintains_events_anywhere(s: Setup) -> None:
    """No regions (ADR 0015): events in Ulm and Berlin are as editable as in Aalen."""
    ulm = s.stored(EventStatus.DRAFT, city="Ulm", postal_code="89073", lat=48.4, lon=10.0)
    berlin = s.stored(EventStatus.PUBLISHED, city="Berlin", postal_code="10115", lat=52.5, lon=13.4)
    assert (await s.get(MODERATOR, ulm.id)).event.id == ulm.id
    assert (await s.publish(MODERATOR, ulm.id)).status is ModStatus.PUBLISHED
    assert (await s.cancel(MODERATOR, berlin.id, None)).status is ModStatus.CANCELLED


async def test_unknown_events_are_not_found(s: Setup) -> None:
    with pytest.raises(NotFoundError):
        await s.get(MODERATOR, uuid4())


async def test_list_drops_unknown_ids(s: Setup) -> None:
    own = s.stored(EventStatus.PUBLISHED)
    rows = await s.list(MODERATOR, ids=frozenset({own.id, uuid4()}))
    assert [row.summary.id for row in rows] == [own.id]


# --- overview (R07-US2) ---------------------------------------------------------------------


async def test_overview_order_status_and_search(s: Setup) -> None:
    s.stored(
        EventStatus.PUBLISHED,
        name="Sommerfest",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
    )
    s.stored(
        EventStatus.PUBLISHED,
        name="Frühlingsfest",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 2),
    )
    s.stored(
        EventStatus.DRAFT,
        name="Lichtermarkt",
        start_date=date(2026, 12, 5),
        end_date=date(2026, 12, 6),
    )
    s.stored(
        EventStatus.CANCELLED,
        name="Herbstmarkt",
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )
    s.stored(EventStatus.DRAFT, name="Ohne Datum", start_date=None, end_date=None)

    rows = await s.list(MODERATOR)

    assert [r.summary.name for r in rows] == [
        "Herbstmarkt",
        "Lichtermarkt",
        "Sommerfest",
        "Frühlingsfest",
        "Ohne Datum",
    ]
    assert [r.status for r in rows][:3] == [ModStatus.CANCELLED, ModStatus.DRAFT, ModStatus.PAST]
    past = await s.list(MODERATOR, status=ModStatus.PAST)
    assert {r.summary.name for r in past} == {"Sommerfest", "Frühlingsfest"}
    found = await s.list(MODERATOR, query="aalen")
    assert len(found) == 5  # all are in Aalen
    assert await s.list(MODERATOR, query="licht") == [rows[1]]


# --- create and edit (R07-US3) ----------------------------------------------------------


async def test_create_always_makes_a_draft(s: Setup) -> None:
    view = await s.create(MODERATOR, EventContent(name="  Herbstfest Wasseralfingen "))
    assert view.event.status is EventStatus.DRAFT
    assert view.event.content.name == "Herbstfest Wasseralfingen"
    assert view.event.content.short_name == "Herbstfest Wassera"
    assert view.event.version == 1
    assert s.events.outbox == []


async def test_create_requires_a_name(s: Setup) -> None:
    with pytest.raises(InvalidInputError):
        await s.create(MODERATOR, EventContent(name="   "))


async def test_update_merges_fields_and_bumps_the_version(s: Setup) -> None:
    event = s.stored(EventStatus.DRAFT)
    view = await s.update(MODERATOR, event.id, {"price": "Frei", "description": None}, 1)
    assert view.event.content.price == "Frei"
    assert view.event.version == 2


async def test_update_with_a_stale_version_conflicts(s: Setup) -> None:
    event = s.stored(EventStatus.DRAFT)
    await s.update(MODERATOR, event.id, {"price": "Frei"}, 1)
    with pytest.raises(ConflictError) as raised:
        await s.update(MODERATOR, event.id, {"price": "5 €"}, 1)
    assert raised.value.code == "version_conflict"


async def test_update_of_a_published_event_records_changed_fields(s: Setup) -> None:
    event = s.stored(EventStatus.PUBLISHED)
    await s.update(MODERATOR, event.id, {"start_date": date(2026, 10, 16)}, 1)
    assert s.events.outbox[0].type is DomainEventType.UPDATED
    assert s.events.outbox[0].changed_fields == ("startDate",)


async def test_cancelled_events_reject_date_changes(s: Setup) -> None:
    event = s.stored(EventStatus.CANCELLED)
    with pytest.raises(ConflictError) as raised:
        await s.update(MODERATOR, event.id, {"start_date": date(2026, 11, 1)}, 1)
    assert raised.value.code == "invalid_transition"


async def test_update_rejects_unknown_fields(s: Setup) -> None:
    event = s.stored(EventStatus.DRAFT)
    with pytest.raises(InvalidInputError):
        await s.update(MODERATOR, event.id, {"status": "published"}, 1)


# --- status changes (R07-US4, US5) --------------------------------------------------------


async def test_publish_with_missing_fields_reports_them(s: Setup) -> None:
    event = s.stored(EventStatus.DRAFT, category_id=None, lat=None)
    with pytest.raises(InvalidInputError) as raised:
        await s.publish(MODERATOR, event.id)
    assert raised.value.fields == {"categoryId": "required", "location": "required"}


async def test_publish_unpublish_cancel_delete(s: Setup) -> None:
    event = s.stored(EventStatus.DRAFT)

    published = await s.publish(MODERATOR, event.id)
    assert published.status is ModStatus.PUBLISHED
    withdrawn = await s.unpublish(MODERATOR, event.id)
    assert withdrawn.status is ModStatus.DRAFT
    await s.publish(MODERATOR, event.id)
    cancelled = await s.cancel(MODERATOR, event.id, "Sturmwarnung")
    assert cancelled.event.content.cancel_reason == "Sturmwarnung"
    await s.delete(MODERATOR, event.id)

    assert _types(s) == [
        DomainEventType.PUBLISHED,
        DomainEventType.UNPUBLISHED,
        DomainEventType.PUBLISHED,
        DomainEventType.CANCELLED,
        DomainEventType.DELETED,
    ]
    with pytest.raises(NotFoundError):
        await s.get(MODERATOR, event.id)


async def test_invalid_transitions_conflict(s: Setup) -> None:
    draft = s.stored(EventStatus.DRAFT)
    with pytest.raises(ConflictError) as raised:
        await s.cancel(MODERATOR, draft.id, None)
    assert raised.value.code == "invalid_transition"
    with pytest.raises(ConflictError):
        await s.unpublish(MODERATOR, draft.id)


# --- outbox (R07-US7) ---------------------------------------------------------------------


async def test_relay_hands_pending_messages_to_the_queue() -> None:
    message = OutboxMessage(uuid4(), "event.published", {"eventId": str(uuid4())})
    outbox, queue = FakeOutboxStore(pending=[message]), FakeEventQueue()
    assert await RelayOutbox(outbox, queue)() == 1
    assert queue.sent == [message]
    assert await RelayOutbox(outbox, queue)() == 0


@pytest.mark.parametrize("event_type", [t.value for t in DomainEventType])
async def test_every_event_invalidates_the_catalog_cache(event_type: str) -> None:
    cache, favorites = FakeCache(), FakeEventFavorites()
    message = OutboxMessage(uuid4(), event_type, {"eventId": str(uuid4())})
    await _handler(cache, favorites)(message)
    assert await cache.generation("catalog") == 1


async def test_deleted_events_lose_their_favorites() -> None:
    favorites = FakeEventFavorites()
    event_id = uuid4()
    message = OutboxMessage(uuid4(), "event.deleted", {"eventId": str(event_id)})
    handle = _handler(FakeCache(), favorites)
    await handle(message)
    await handle(message)  # delivered twice: still the same state
    assert favorites.removed == [event_id, event_id]


async def test_event_and_ai_results_reach_the_notifications() -> None:
    """R11: published/updated/cancelled and AI results go to the notification consumer."""
    seen: list[str] = []

    async def notify(event_type: str, payload: Mapping[str, object]) -> None:
        seen.append(event_type)

    handle = HandleDomainEvent(FakeCache(), FakeEventFavorites(), _ignore, _ignore, None, notify)
    for event_type in ["event.published", "event.cancelled", "event.deleted"]:
        await handle(OutboxMessage(uuid4(), event_type, {"eventId": str(uuid4())}))
    for event_type in ["ai_search.completed", "ai_search.failed"]:
        await handle(OutboxMessage(uuid4(), event_type, {"jobId": str(uuid4())}))
    await handle(
        OutboxMessage(
            uuid4(), "friendship.created", {"userId": str(uuid4()), "friendId": str(uuid4())}
        )
    )
    # Deleted events notify nobody; their favorites are removed instead.
    assert seen == [
        "event.published",
        "event.cancelled",
        "ai_search.completed",
        "ai_search.failed",
        "friendship.created",
    ]


async def test_unknown_events_are_ignored() -> None:
    cache = FakeCache()
    await _handler(cache, FakeEventFavorites())(OutboxMessage(uuid4(), "x.y", {}))
    assert await cache.generation("catalog") == 0


async def test_purge_keeps_14_days() -> None:
    outbox = FakeOutboxStore()
    await PurgeOutbox(outbox, now=lambda: datetime(2026, 10, 15, tzinfo=UTC))()
    assert outbox.purged_before == [datetime(2026, 10, 1, tzinfo=UTC)]
