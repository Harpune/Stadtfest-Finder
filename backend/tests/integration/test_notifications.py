"""Notification adapters against PostgreSQL/PostGIS (R11)."""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.persistence.accounts import SqlUserRepository
from stadtfest.adapters.outbound.persistence.favorites import SqlFavoriteRepository
from stadtfest.adapters.outbound.persistence.models import (
    AppUserRow,
    DeviceRow,
    EventRow,
    NotificationRow,
    NotificationSettingsRow,
)
from stadtfest.adapters.outbound.persistence.notifications import (
    SqlDeviceStore,
    SqlNotificationStore,
    SqlRecipients,
    SqlSettingsStore,
)
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.notifications.ports import Device, DevicePlatform, PushProvider
from stadtfest.application.notifications.use_cases import FANOUT_BATCH, Notify
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.notifications.notification import EventFacts, NotificationType
from stadtfest.domain.notifications.settings import Home, NotificationSettings
from tests.fakes import FakePushJobs
from tests.integration.seed_support import load

pytestmark = pytest.mark.integration

TODAY = date(2026, 9, 25)
NOW = datetime(2026, 9, 25, 7, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
async def engine(migrated_postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_url)
    await load(async_sessionmaker(engine), TODAY)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="module")
def users(sessions: async_sessionmaker[AsyncSession]) -> SqlUserRepository:
    return SqlUserRepository(sessions)


async def _user(users: SqlUserRepository) -> tuple[str, UUID]:
    subject = f"sub-{uuid4()}"
    record = await users.get_or_create(subject, "Lena", "Beispiel")
    return subject, record.id


async def _published_event(
    sessions: async_sessionmaker[AsyncSession], start: date | None = None
) -> tuple[UUID, GeoPoint]:
    """A published event with location; optionally moved to a new start date."""
    async with sessions.begin() as session:
        row = (
            await session.execute(
                select(
                    EventRow.id,
                    func.ST_Y(cast(EventRow.location, Geometry)),
                    func.ST_X(cast(EventRow.location, Geometry)),
                )
                .where(
                    EventRow.status == "published",
                    EventRow.deleted_at.is_(None),
                    EventRow.location.is_not(None),
                )
                .order_by(EventRow.id)
                .limit(1)
            )
        ).one()
        if start is not None:
            await session.execute(
                update(EventRow)
                .where(EventRow.id == row[0])
                .values(start_date=start, end_date=start + timedelta(days=2))
            )
    return row[0], GeoPoint(row[1], row[2])


async def test_add_is_idempotent_per_key_and_pages_newest_first(
    sessions: async_sessionmaker[AsyncSession], users: SqlUserRepository
) -> None:
    store = SqlNotificationStore(sessions)
    _, lena = await _user(users)
    event_id, _ = await _published_event(sessions)

    first = await store.add([lena], NotificationType.CHANGE, event_id, "change:a", NOW)
    again = await store.add([lena], NotificationType.CHANGE, event_id, "change:a", NOW)
    later = await store.add(
        [lena], NotificationType.CHANGE, event_id, "change:b", NOW + timedelta(hours=1)
    )

    assert len(first) == 1
    assert again == []
    page = await store.page(lena, None, 10)
    assert [n.notification.id for n in page] == [*later, *first]
    assert isinstance(page[0].facts, EventFacts)
    assert page[0].facts.name
    assert await store.unread_count(lena) == 2
    assert await store.mark_read(lena, first[0])
    assert not await store.mark_read(uuid4(), first[0])
    stranger = uuid4()
    assert await store.unread_counts([lena, stranger]) == {lena: 1, stranger: 0}
    await store.mark_all_read(lena)
    assert await store.unread_count(lena) == 0
    assert [n.notification.id for n in await store.unpushed([*first, *later])] == [*first, *later]
    await store.mark_pushed(first)
    assert [n.notification.id for n in await store.unpushed([*first, *later])] == later


async def test_settings_round_trip_with_home_center(
    sessions: async_sessionmaker[AsyncSession], users: SqlUserRepository
) -> None:
    store = SqlSettingsStore(sessions)
    _, lena = await _user(users)
    assert await store.get(lena) == NotificationSettings()

    settings = NotificationSettings(
        remind_days_before=3,
        home=Home("73430", "Aalen", GeoPoint(48.8378, 10.0933)),
        near_radius_km=50,
        change=False,
    )
    await store.put(lena, settings)
    stored = await store.get(lena)
    assert stored.home is not None
    assert stored.home.location.lat == pytest.approx(48.8378)
    assert stored == settings
    await store.put(lena, NotificationSettings())
    assert await store.get(lena) == NotificationSettings()


async def test_near_home_uses_each_users_radius(
    sessions: async_sessionmaker[AsyncSession], users: SqlUserRepository
) -> None:
    settings, recipients = SqlSettingsStore(sessions), SqlRecipients(sessions)
    event_id, location = await _published_event(sessions)
    _, close = await _user(users)
    _, far = await _user(users)
    _, no_home = await _user(users)
    # About 20 km north of the event.
    home = GeoPoint(location.lat + 0.18, location.lon)
    await settings.put(
        close, NotificationSettings(home=Home("73430", "A", home), near_radius_km=25)
    )
    await settings.put(far, NotificationSettings(home=Home("73430", "A", home), near_radius_km=10))
    await settings.put(no_home, NotificationSettings())

    found = await recipients.near_home(event_id)

    assert close in found
    assert far not in found
    assert no_home not in found


async def test_reminders_follow_remind_days_before(
    sessions: async_sessionmaker[AsyncSession], users: SqlUserRepository
) -> None:
    favorites = SqlFavoriteRepository(sessions, ImageUrls("https://img.test/x"))
    settings, recipients = SqlSettingsStore(sessions), SqlRecipients(sessions)
    event_id, _ = await _published_event(sessions, start=TODAY + timedelta(days=3))
    default_subject, default_user = await _user(users)
    three_subject, three_days = await _user(users)
    await settings.put(three_days, NotificationSettings(remind_days_before=3))
    await favorites.add(default_subject, event_id)
    await favorites.add(three_subject, event_id)

    in_two_days = await recipients.reminders(TODAY + timedelta(days=2))
    assert default_user in in_two_days.get(event_id, [])  # default: 1 day before
    assert three_days not in in_two_days.get(event_id, [])
    today = await recipients.reminders(TODAY)
    assert three_days in today.get(event_id, [])
    assert default_user not in today.get(event_id, [])
    assert set(await recipients.favorite_holders(event_id)) >= {default_user, three_days}


async def test_fanout_to_2000_recipients(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    event_id, _ = await _published_event(sessions)
    async with sessions.begin() as session:
        ids = [uuid4() for _ in range(2000)]
        await session.execute(
            AppUserRow.__table__.insert(),
            [{"id": i, "idp_subject": f"bulk-{i}"} for i in ids],
        )
    jobs = FakePushJobs()
    notify = Notify(SqlNotificationStore(sessions), jobs, lambda: NOW)

    assert await notify(NotificationType.CANCEL, event_id, ids) == 2000
    assert [len(batch) for batch in jobs.pushes] == [FANOUT_BATCH] * 4
    assert await notify(NotificationType.CANCEL, event_id, ids) == 0


async def test_devices_move_between_users_and_expire(
    sessions: async_sessionmaker[AsyncSession], users: SqlUserRepository
) -> None:
    devices = SqlDeviceStore(sessions)
    _, lena = await _user(users)
    _, tim = await _user(users)
    phone = Device(f"ExponentPushToken[{uuid4()}]", DevicePlatform.IOS, PushProvider.EXPO)
    old = Device(f"fcm-{uuid4()}", DevicePlatform.ANDROID, PushProvider.DIRECT)

    await devices.register(lena, phone, NOW)
    await devices.register(tim, phone, NOW)
    await devices.register(lena, old, NOW - timedelta(days=100))

    assert await devices.for_users([lena, tim], PushProvider.EXPO) == {tim: [phone]}
    await devices.remove(lena, phone.token)
    assert await devices.for_users([tim], PushProvider.EXPO) == {tim: [phone]}
    assert await devices.purge_inactive(NOW - timedelta(days=90)) >= 1
    assert await devices.for_users([lena], PushProvider.DIRECT) == {}
    await devices.remove_tokens([phone.token])
    assert await devices.for_users([tim], PushProvider.EXPO) == {}


async def test_account_deletion_removes_notifications_settings_and_devices(
    sessions: async_sessionmaker[AsyncSession], users: SqlUserRepository
) -> None:
    subject, lena = await _user(users)
    event_id, _ = await _published_event(sessions)
    await SqlNotificationStore(sessions).add(
        [lena], NotificationType.CANCEL, event_id, f"cancel:{uuid4()}", NOW
    )
    await SqlSettingsStore(sessions).put(lena, NotificationSettings(change=False))
    await SqlDeviceStore(sessions).register(
        lena, Device(f"t-{uuid4()}", DevicePlatform.IOS, PushProvider.EXPO), NOW
    )

    assert await users.delete_personal_data(subject)

    async with sessions() as session:
        for table in (NotificationRow, NotificationSettingsRow, DeviceRow):
            remaining = await session.scalar(
                select(func.count()).select_from(table).where(table.user_id == lena)
            )
            assert remaining == 0


async def test_delete_only_removes_the_own_notification(
    sessions: async_sessionmaker[AsyncSession], users: SqlUserRepository
) -> None:
    store = SqlNotificationStore(sessions)
    _, lena = await _user(users)
    _, tim = await _user(users)
    event_id, _ = await _published_event(sessions)
    [mine] = await store.add([lena], NotificationType.CANCEL, event_id, f"x:{uuid4()}", NOW)

    await store.delete(tim, mine)
    assert len(await store.page(lena, None, 10)) == 1
    await store.delete(lena, mine)
    assert await store.page(lena, None, 10) == []
