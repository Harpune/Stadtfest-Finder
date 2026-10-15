"""Notification use cases with fake adapters (R11)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest

from stadtfest.application.geocoding.ports import Place, PlaceKind
from stadtfest.application.notifications.ports import Device, DevicePlatform, PushProvider
from stadtfest.application.notifications.use_cases import (
    FANOUT_BATCH,
    CheckPushReceipts,
    DeleteNotification,
    GetNotificationSettings,
    HomeInput,
    ListNotifications,
    MarkAllNotificationsRead,
    MarkNotificationRead,
    Notify,
    NotifyForDomainEvent,
    PurgeNotifications,
    PushNotifications,
    PushToModerator,
    RegisterDevice,
    RemoveDevice,
    SendReminders,
    SettingsInput,
    UpdateNotificationSettings,
)
from stadtfest.application.shared.errors import (
    InvalidInputError,
    NotFoundError,
    ServiceUnavailableError,
)
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.identity.principal import Principal, Role
from stadtfest.domain.notifications.notification import (
    EventFacts,
    ListFacts,
    NotificationType,
    PersonFacts,
)
from stadtfest.domain.notifications.settings import Home, NotificationSettings
from tests.fakes import (
    FakeAccountResolver,
    FakeAiSearchOwners,
    FakeDeviceStore,
    FakeGeocoding,
    FakeNotificationStore,
    FakePushJobs,
    FakePushSender,
    FakeRecipients,
    FakeSettingsStore,
    FixedClock,
)

LENA = Principal("sub-lena", frozenset({Role.USER}))
TIM = Principal("sub-tim", frozenset({Role.USER}))
LENA_ID = uuid5(NAMESPACE_URL, LENA.subject)
TIM_ID = uuid5(NAMESPACE_URL, TIM.subject)
MIA = uuid4()
NOW = datetime(2026, 10, 1, 7, 0, tzinfo=UTC)
FEST = uuid4()
FACTS = EventFacts("Reichsstädter Tage", "Aalen", date(2026, 10, 2), date(2026, 10, 13))
AALEN = Place("73430 Aalen", "Aalen", GeoPoint(48.8378, 10.0933), PlaceKind.POSTCODE, "73430")


@dataclass
class Setup:
    store: FakeNotificationStore = field(
        default_factory=lambda: FakeNotificationStore(events={FEST: FACTS})
    )
    settings: FakeSettingsStore = field(default_factory=FakeSettingsStore)
    recipients: FakeRecipients = field(default_factory=FakeRecipients)
    devices: FakeDeviceStore = field(default_factory=FakeDeviceStore)
    sender: FakePushSender = field(default_factory=FakePushSender)
    jobs: FakePushJobs = field(default_factory=FakePushJobs)
    owners: FakeAiSearchOwners = field(default_factory=FakeAiSearchOwners)
    geocoding: FakeGeocoding = field(default_factory=lambda: FakeGeocoding([AALEN]))
    accounts: FakeAccountResolver = field(default_factory=FakeAccountResolver)
    now: datetime = NOW

    def notify(self) -> Notify:
        return Notify(self.store, self.jobs, lambda: self.now)

    def push(self) -> PushNotifications:
        return PushNotifications(self.store, self.settings, self.devices, self.sender, self.jobs)

    def consumer(self) -> NotifyForDomainEvent:
        return NotifyForDomainEvent(
            self.recipients,
            self.notify(),
            PushToModerator(self.owners, self.devices, self.sender, self.jobs),
        )

    def device(self, user_id: UUID, token: str, provider: PushProvider = PushProvider.EXPO) -> None:
        self.devices.devices[token] = (
            user_id,
            Device(token, DevicePlatform.ANDROID, provider),
            NOW,
        )


@pytest.fixture
def s() -> Setup:
    return Setup()


# --- list --------------------------------------------------------------------------------


async def test_list_renders_texts_pages_and_counts_unread(s: Setup) -> None:
    for hours in range(3):  # one change per hour: not combined
        s.now = NOW + timedelta(hours=hours)
        await s.notify()(NotificationType.CHANGE, FEST, [LENA_ID])
    list_ = ListNotifications(s.store, s.accounts)

    first = await list_(LENA, None, 2)
    assert [item.text.startswith("Bei Reichsstädter Tage") for item in first.items] == [True] * 2
    assert first.unread == 3
    assert first.next_cursor is not None
    second = await list_(LENA, first.next_cursor, 2)
    assert len(second.items) == 1
    assert second.next_cursor is None
    assert first.items[0].created_at > first.items[1].created_at > second.items[0].created_at


async def test_foreign_or_invalid_cursor_is_rejected(s: Setup) -> None:
    with pytest.raises(InvalidInputError):
        await ListNotifications(s.store, s.accounts)(LENA, "nicht-vom-server", 20)


async def test_notifications_of_deleted_events_disappear(s: Setup) -> None:
    await s.notify()(NotificationType.CANCEL, FEST, [LENA_ID])
    s.store.deleted_events.add(FEST)
    listing = await ListNotifications(s.store, s.accounts)(LENA, None, 20)
    assert listing.items == []
    assert listing.unread == 0


async def test_mark_read_only_own_and_all(s: Setup) -> None:
    await s.notify()(NotificationType.CANCEL, FEST, [LENA_ID, TIM_ID])
    lena_note = next(n for n in s.store.rows if n.user_id == LENA_ID)
    with pytest.raises(NotFoundError):
        await MarkNotificationRead(s.store, s.accounts)(TIM, lena_note.id)
    await MarkNotificationRead(s.store, s.accounts)(LENA, lena_note.id)
    assert await s.store.unread_count(LENA_ID) == 0
    await MarkAllNotificationsRead(s.store, s.accounts)(TIM)
    assert await s.store.unread_count(TIM_ID) == 0


# --- settings ----------------------------------------------------------------------------


def _update(**changes: object) -> SettingsInput:
    values: dict[str, object] = {
        "remind": True,
        "remind_days_before": 1,
        "near": True,
        "home": HomeInput("73430", "Aalen"),
        "near_radius_km": 25,
        "change": True,
        "invite": True,
        "rsvp": True,
    }
    return SettingsInput(**(values | changes))  # type: ignore[arg-type]


async def test_settings_default_and_home_from_geocoding(s: Setup) -> None:
    assert await GetNotificationSettings(s.settings, s.accounts)(LENA) == NotificationSettings()
    update = UpdateNotificationSettings(s.settings, s.accounts, s.geocoding)

    stored = await update(LENA, _update(remind_days_before=3))

    assert stored.home == Home("73430", "Aalen", AALEN.location)
    assert s.settings.stored[LENA_ID].remind_days_before == 3
    # Switching a toggle sends the whole object again; the known center is reused.
    await update(LENA, _update(change=False))
    assert s.geocoding.search_calls == ["73430"]


@pytest.mark.parametrize(
    ("changes", "field_name"),
    [
        ({"near_radius_km": 3}, "nearRadiusKm"),
        ({"remind_days_before": 2}, "remindDaysBefore"),
        ({"home": HomeInput("7343", "Aalen")}, "home.postalCode"),
        ({"home": HomeInput("99999", "Nirgendwo")}, "home.postalCode"),
    ],
)
async def test_invalid_settings_are_422(
    s: Setup, changes: dict[str, object], field_name: str
) -> None:
    with pytest.raises(InvalidInputError) as raised:
        await UpdateNotificationSettings(s.settings, s.accounts, s.geocoding)(
            LENA, _update(**changes)
        )
    assert field_name in raised.value.fields
    assert LENA_ID not in s.settings.stored


async def test_unknown_postal_code_and_geocoder_down(s: Setup) -> None:
    update = UpdateNotificationSettings(s.settings, s.accounts, s.geocoding)
    with pytest.raises(InvalidInputError) as raised:
        await update(LENA, _update(home=HomeInput("89073", "Ulm")))
    assert raised.value.code == "postal_code_unknown"
    s.geocoding.unavailable = True
    with pytest.raises(ServiceUnavailableError):
        await update(LENA, _update())


async def test_removing_the_home(s: Setup) -> None:
    update = UpdateNotificationSettings(s.settings, s.accounts, s.geocoding)
    await update(LENA, _update())
    assert (await update(LENA, _update(home=None))).home is None


# --- devices -----------------------------------------------------------------------------


async def test_register_and_remove_devices(s: Setup) -> None:
    register = RegisterDevice(s.devices, s.accounts, lambda: NOW)
    await register(LENA, "ExponentPushToken[a]", DevicePlatform.IOS, PushProvider.EXPO)
    # The same phone signs in with another account: the token moves.
    await register(TIM, "ExponentPushToken[a]", DevicePlatform.IOS, PushProvider.EXPO)
    assert s.devices.devices["ExponentPushToken[a]"][0] == TIM_ID
    await RemoveDevice(s.devices, s.accounts)(LENA, "ExponentPushToken[a]")
    assert "ExponentPushToken[a]" in s.devices.devices  # not Lena's anymore
    await RemoveDevice(s.devices, s.accounts)(TIM, "ExponentPushToken[a]")
    assert s.devices.devices == {}
    with pytest.raises(InvalidInputError):
        await register(LENA, "  ", DevicePlatform.IOS, PushProvider.EXPO)
    with pytest.raises(InvalidInputError):
        await register(LENA, "t", DevicePlatform.IOS, PushProvider.DISABLED)


# --- triggers ----------------------------------------------------------------------------


async def test_near_only_on_first_publication(s: Setup) -> None:
    s.recipients.near[FEST] = [LENA_ID]
    consumer = s.consumer()
    payload: dict[str, object] = {"eventId": str(FEST), "changedFields": []}
    assert await consumer("event.published", payload) == 0
    assert await consumer("event.published", payload | {"firstPublication": True}) == 1
    assert s.store.rows[0].type is NotificationType.NEAR


async def test_change_only_for_relevant_fields_and_combined_per_hour(s: Setup) -> None:
    s.recipients.holders[FEST] = [LENA_ID, TIM_ID]
    consumer = s.consumer()
    text_only = {"eventId": str(FEST), "changedFields": ["description", "price"]}
    assert await consumer("event.updated", text_only) == 0
    moved = {"eventId": str(FEST), "changedFields": ["startDate", "endDate"]}
    assert await consumer("event.updated", moved) == 2
    assert await consumer("event.updated", moved) == 0  # same hour: combined


async def test_cancel_reaches_all_favorite_holders(s: Setup) -> None:
    s.recipients.holders[FEST] = [LENA_ID, TIM_ID]
    assert await s.consumer()("event.cancelled", {"eventId": str(FEST)}) == 2
    assert {n.type for n in s.store.rows} == {NotificationType.CANCEL}
    assert await s.consumer()("event.cancelled", {"eventId": str(FEST)}) == 0  # redelivery


async def test_other_events_are_ignored(s: Setup) -> None:
    s.recipients.holders[FEST] = [LENA_ID]
    consumer = s.consumer()
    assert await consumer("event.unpublished", {"eventId": str(FEST)}) == 0
    assert await consumer("event.deleted", {"eventId": str(FEST)}) == 0
    assert await consumer("category.changed", {}) == 0


async def test_large_fanout_is_split_into_push_jobs(s: Setup) -> None:
    users = [uuid4() for _ in range(FANOUT_BATCH * 2 + 1)]
    assert await s.notify()(NotificationType.CANCEL, FEST, users) == len(users)
    assert [len(batch) for batch in s.jobs.pushes] == [FANOUT_BATCH, FANOUT_BATCH, 1]


async def test_reminders_per_day(s: Setup) -> None:
    s.recipients.due[date(2026, 10, 1)] = {FEST: [LENA_ID]}
    remind = SendReminders(s.recipients, s.notify(), FixedClock(date(2026, 10, 1)))
    assert await remind() == 1
    assert await remind() == 0  # at most one reminder per event and day
    listing = await ListNotifications(s.store, s.accounts)(LENA, None, 20)
    assert listing.items[0].text.startswith("Reichsstädter Tage beginnt morgen")


# --- push --------------------------------------------------------------------------------


async def test_push_respects_settings_and_carries_ids_only(s: Setup) -> None:
    s.settings.stored[TIM_ID] = NotificationSettings(change=False)
    s.device(LENA_ID, "lena-phone")
    s.device(TIM_ID, "tim-phone")
    s.device(LENA_ID, "lena-old", PushProvider.DIRECT)  # registered for another provider
    await s.notify()(NotificationType.CANCEL, FEST, [LENA_ID, TIM_ID])

    assert await s.push()(s.jobs.pushes[0]) == 1

    [message] = s.sender.sent
    assert message.token == "lena-phone"
    assert (message.title, message.body) == (
        "Fest abgesagt",
        "Eines deiner Lieblingsfeste fällt aus.",
    )
    assert message.badge == 1
    assert set(message.data) == {"notificationId", "type", "targetType", "targetId"}
    assert message.data["targetId"] == str(FEST)
    assert "Reichsstädter" not in str(message)
    # Muted types stay in the list.
    assert await s.store.unread_count(TIM_ID) == 1
    # A second run of the same job sends nothing again.
    assert await s.push()(s.jobs.pushes[0]) == 0


async def test_invalid_tokens_are_removed_and_receipts_checked_later(s: Setup) -> None:
    s.device(LENA_ID, "gone")
    s.device(LENA_ID, "ok")
    s.sender.invalid = {"gone"}
    s.sender.receipts = {"ticket-1": "ok"}
    await s.notify()(NotificationType.CANCEL, FEST, [LENA_ID])

    await s.push()(s.jobs.pushes[0])

    assert set(s.devices.devices) == {"ok"}
    assert s.jobs.receipt_checks == [{"ticket-1": "ok"}]
    s.sender.invalid_by_receipt = {"ok"}
    assert await CheckPushReceipts(s.sender, s.devices)({"ticket-1": "ok"}) == 1
    assert s.devices.devices == {}


async def test_disabled_provider_sends_nothing(s: Setup) -> None:
    s.sender.provider = PushProvider.DISABLED
    s.device(LENA_ID, "lena-phone")
    await s.notify()(NotificationType.CANCEL, FEST, [LENA_ID])
    assert await s.push()(s.jobs.pushes[0]) == 0
    assert s.sender.sent == []


async def test_ai_search_result_is_pushed_to_its_moderator_only(s: Setup) -> None:
    job = uuid4()
    s.owners.owners[job] = LENA_ID
    s.device(LENA_ID, "mod-phone")
    s.device(TIM_ID, "tim-phone")

    assert await s.consumer()("ai_search.completed", {"jobId": str(job)}) == 1

    [message] = s.sender.sent
    assert message.token == "mod-phone"
    assert message.title == "Suche abgeschlossen"
    assert message.data == {
        "type": "ai_search_completed",
        "targetType": "aiSearch",
        "targetId": str(job),
    }
    assert s.store.rows == []  # push only, no list entry
    assert await s.consumer()("ai_search.failed", {"jobId": str(uuid4())}) == 0  # unknown job


async def test_purge_after_retention(s: Setup) -> None:
    s.now = NOW - timedelta(days=400)
    await s.notify()(NotificationType.CANCEL, FEST, [LENA_ID])
    s.devices.devices["old"] = (
        LENA_ID,
        Device("old", DevicePlatform.IOS, PushProvider.EXPO),
        NOW - timedelta(days=91),
    )
    s.device(LENA_ID, "fresh")
    result = await PurgeNotifications(s.store, s.devices, lambda: NOW)()
    assert (result.notifications, result.devices) == (1, 1)
    assert set(s.devices.devices) == {"fresh"}


async def test_delete_only_own_notifications(s: Setup) -> None:
    await s.notify()(NotificationType.CANCEL, FEST, [LENA_ID, TIM_ID])
    lena_note = next(n for n in s.store.rows if n.user_id == LENA_ID)
    delete = DeleteNotification(s.store, s.accounts)

    await delete(TIM, lena_note.id)  # someone else's: left alone, no error
    assert lena_note in s.store.rows
    await delete(LENA, lena_note.id)
    await delete(LENA, lena_note.id)  # idempotent
    assert [n.user_id for n in s.store.rows] == [TIM_ID]


async def test_friend_added_is_listed_with_the_name_but_never_pushed(s: Setup) -> None:
    s.store.events[TIM_ID] = PersonFacts("Tim", "Krause")
    s.device(LENA_ID, "lena-phone")
    payload = {"userId": str(LENA_ID), "friendId": str(TIM_ID)}

    assert await s.consumer()("friendship.created", payload) == 1
    assert await s.consumer()("friendship.created", payload) == 0  # redelivery

    listing = await ListNotifications(s.store, s.accounts)(LENA, None, 20)
    assert listing.items[0].text == "Tim Krause ist jetzt mit dir befreundet."
    assert listing.items[0].subject_id == TIM_ID
    assert await s.push()(s.jobs.pushes[0]) == 0
    assert s.sender.sent == []


async def test_list_added_names_list_and_actor_and_follows_the_invite_setting(s: Setup) -> None:
    list_id = uuid4()
    s.store.events[list_id] = ListFacts("Weihnachtsmarkt-Tour", "Lena")
    s.device(TIM_ID, "tim-phone")
    s.device(LENA_ID, "lena-phone")
    s.settings.stored[LENA_ID] = NotificationSettings(invite=False)
    payload = {"listId": str(list_id), "userIds": [str(TIM_ID), str(LENA_ID)], "actorId": str(MIA)}

    assert await s.consumer()("list.members_added", payload) == 2

    listing = await ListNotifications(s.store, s.accounts)(TIM, None, 20)
    assert listing.items[0].text == (
        "Lena hat dich zur Liste \u201aWeihnachtsmarkt-Tour\u2018 hinzugefügt."
    )
    assert listing.items[0].subject_id == list_id
    assert s.store.actors[list_id] == MIA
    await s.push()(s.jobs.pushes[0])
    [message] = s.sender.sent  # Lena turned invitations off
    assert message.token == "tim-phone"
    assert message.data["targetType"] == "list"
