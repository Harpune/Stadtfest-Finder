"""Notification use cases (R11).

Delivery: domain event or schedule -> recipients -> list entries (always) -> push job per
batch -> push only for types the user enabled -> invalid tokens are removed (R11-US3).
"""

from __future__ import annotations

import base64
import binascii
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import batched
from uuid import UUID

from stadtfest.application.geocoding.ports import GeocodingPort, GeocodingUnavailableError
from stadtfest.application.notifications.ports import (
    AccountResolver,
    AiSearchOwners,
    Device,
    DevicePlatform,
    DeviceStore,
    NotificationStore,
    PageCursor,
    PushJobs,
    PushMessage,
    PushProvider,
    PushSender,
    Recipients,
    SettingsStore,
    StoredNotification,
)
from stadtfest.application.shared.errors import (
    InvalidInputError,
    NotFoundError,
    ServiceUnavailableError,
)
from stadtfest.application.shared.ports import Clock
from stadtfest.domain.ai_ingestion.job import AiSearchEventType
from stadtfest.domain.events.geo import PostalCode
from stadtfest.domain.events.maintenance import DomainEventType
from stadtfest.domain.identity.principal import Principal
from stadtfest.domain.notifications.notification import (
    PUSH_TEXTS,
    NotificationType,
    PushOnlyType,
    dedupe_key,
    is_relevant_change,
    render_text,
)
from stadtfest.domain.notifications.settings import (
    Home,
    InvalidSettingsError,
    NotificationSettings,
)

logger = logging.getLogger(__name__)

# Recipients per push job, so that a large cancellation does not block the worker.
FANOUT_BATCH = 500
RETENTION = timedelta(days=365)
DEVICE_IDLE = timedelta(days=90)
POSTAL_CODE_UNKNOWN = "postal_code_unknown"
GEOCODING_UNAVAILABLE = "geocoding_unavailable"

Now = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


# --- list --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NotificationItem:
    """A notification with its rendered text."""

    id: UUID
    type: NotificationType
    text: str
    event_id: UUID
    read: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class NotificationListing:
    """One page plus the unread count for the badge."""

    items: list[NotificationItem]
    next_cursor: str | None
    unread: int


def encode_cursor(cursor: PageCursor) -> str:
    """Opaque cursor for the next page."""
    raw = f"{cursor.created_at.isoformat()}|{cursor.id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(value: str) -> PageCursor:
    """Read a cursor issued by `encode_cursor`.

    Raises:
        InvalidInputError: If the cursor was not issued by the server.
    """
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
        created, ident = raw.split("|")
        cursor = PageCursor(datetime.fromisoformat(created), UUID(ident))
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise InvalidInputError({"cursor": "invalid"}) from None
    if cursor.created_at.tzinfo is None:
        raise InvalidInputError({"cursor": "invalid"})
    return cursor


class ListNotifications:
    """The caller's notifications, newest first (R11-US1)."""

    def __init__(self, store: NotificationStore, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._store = store
        self._accounts = accounts

    async def __call__(
        self, principal: Principal, cursor: str | None, limit: int
    ) -> NotificationListing:
        """Return one page with rendered texts.

        Raises:
            InvalidInputError: Unknown cursor.
        """
        after = decode_cursor(cursor) if cursor else None
        user_id = await self._accounts(principal)
        rows = await self._store.page(user_id, after, limit + 1)
        items = [
            NotificationItem(
                id=row.notification.id,
                type=row.notification.type,
                text=render_text(row.notification.type, row.event, row.notification.created_at),
                event_id=row.notification.event_id,
                read=row.notification.read,
                created_at=row.notification.created_at,
            )
            for row in rows[:limit]
        ]
        next_cursor = None
        if len(rows) > limit:
            last = items[-1]
            next_cursor = encode_cursor(PageCursor(last.created_at, last.id))
        return NotificationListing(items, next_cursor, await self._store.unread_count(user_id))


class MarkNotificationRead:
    """Mark one of the caller's notifications as read (idempotent)."""

    def __init__(self, store: NotificationStore, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._store = store
        self._accounts = accounts

    async def __call__(self, principal: Principal, notification_id: UUID) -> None:
        """Mark it read.

        Raises:
            NotFoundError: Unknown or another user's notification.
        """
        user_id = await self._accounts(principal)
        if not await self._store.mark_read(user_id, notification_id):
            raise NotFoundError


class DeleteNotification:
    """Remove one of the caller's notifications from the list (swipe, idempotent)."""

    def __init__(self, store: NotificationStore, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._store = store
        self._accounts = accounts

    async def __call__(self, principal: Principal, notification_id: UUID) -> None:
        """Delete it; other users' notifications are left alone."""
        await self._store.delete(await self._accounts(principal), notification_id)


class MarkAllNotificationsRead:
    """Mark all of the caller's notifications as read."""

    def __init__(self, store: NotificationStore, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._store = store
        self._accounts = accounts

    async def __call__(self, principal: Principal) -> None:
        """Mark everything read."""
        await self._store.mark_all_read(await self._accounts(principal))


# --- settings ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HomeInput:
    """Home as sent by the app: ZIP code and place name, never coordinates (E-10)."""

    postal_code: str
    place_name: str


@dataclass(frozen=True, slots=True)
class SettingsInput:
    """The whole settings object of a `PUT`."""

    remind: bool
    remind_days_before: int
    near: bool
    home: HomeInput | None
    near_radius_km: int
    change: bool
    invite: bool
    rsvp: bool


class GetNotificationSettings:
    """The caller's settings, defaults until the first change (R11-US2)."""

    def __init__(self, settings: SettingsStore, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._settings = settings
        self._accounts = accounts

    async def __call__(self, principal: Principal) -> NotificationSettings:
        """Return the settings."""
        return await self._settings.get(await self._accounts(principal))


class UpdateNotificationSettings:
    """Replace the caller's settings; the home is stored as ZIP code center (E-10)."""

    def __init__(
        self, settings: SettingsStore, accounts: AccountResolver, geocoding: GeocodingPort
    ) -> None:
        """Create the use case."""
        self._settings = settings
        self._accounts = accounts
        self._geocoding = geocoding

    async def __call__(self, principal: Principal, update: SettingsInput) -> NotificationSettings:
        """Validate, resolve the home and store.

        Raises:
            InvalidInputError: Values out of range or `postal_code_unknown`.
            ServiceUnavailableError: `geocoding_unavailable`.
        """
        user_id = await self._accounts(principal)
        current = await self._settings.get(user_id)
        home = await self._home(update.home, current.home)
        try:
            settings = NotificationSettings(
                remind=update.remind,
                remind_days_before=update.remind_days_before,
                near=update.near,
                home=home,
                near_radius_km=update.near_radius_km,
                change=update.change,
                invite=update.invite,
                rsvp=update.rsvp,
            )
        except InvalidSettingsError as error:
            raise InvalidInputError(error.fields) from None
        await self._settings.put(user_id, settings)
        return settings

    async def _home(self, given: HomeInput | None, current: Home | None) -> Home | None:
        if given is None:
            return None
        code = given.postal_code.strip()
        place_name = given.place_name.strip()
        if current is not None and current.postal_code == code:
            # Toggling a switch sends the whole object; keep the known center.
            return Home(code, place_name, current.location)
        if not PostalCode.is_valid(code):
            raise InvalidInputError({"home.postalCode": "invalid"})
        try:
            places = await self._geocoding.search(code, 5)
        except GeocodingUnavailableError:
            raise ServiceUnavailableError(GEOCODING_UNAVAILABLE) from None
        place = next((p for p in places if p.postal_code == code), None)
        if place is None:
            raise InvalidInputError({"home.postalCode": POSTAL_CODE_UNKNOWN}, POSTAL_CODE_UNKNOWN)
        return Home(code, place_name, place.location)


# --- devices -----------------------------------------------------------------------------


class RegisterDevice:
    """Register the caller's push token after the permission and every sign-in (R11-US5)."""

    def __init__(
        self, devices: DeviceStore, accounts: AccountResolver, now: Now = _utc_now
    ) -> None:
        """Create the use case."""
        self._devices = devices
        self._accounts = accounts
        self._now = now

    async def __call__(
        self, principal: Principal, token: str, platform: DevicePlatform, provider: PushProvider
    ) -> None:
        """Store the token (idempotent; refreshes `last_seen_at`).

        Raises:
            InvalidInputError: Empty token or provider `disabled`.
        """
        token = token.strip()
        if not token:
            raise InvalidInputError({"token": "required"})
        if provider is PushProvider.DISABLED:
            raise InvalidInputError({"provider": "invalid"})
        user_id = await self._accounts(principal)
        await self._devices.register(user_id, Device(token, platform, provider), self._now())


class RemoveDevice:
    """Remove the caller's push token on sign-out (idempotent)."""

    def __init__(self, devices: DeviceStore, accounts: AccountResolver) -> None:
        """Create the use case."""
        self._devices = devices
        self._accounts = accounts

    async def __call__(self, principal: Principal, token: str) -> None:
        """Delete the token if it is the caller's."""
        await self._devices.remove(await self._accounts(principal), token)


# --- delivery ----------------------------------------------------------------------------


class Notify:
    """Fan-out: one list entry per recipient, pushes in batches of `FANOUT_BATCH`."""

    def __init__(self, store: NotificationStore, jobs: PushJobs, now: Now = _utc_now) -> None:
        """Create the use case."""
        self._store = store
        self._jobs = jobs
        self._now = now

    async def __call__(
        self, notification_type: NotificationType, event_id: UUID, user_ids: Sequence[UUID]
    ) -> int:
        """Store the notifications and enqueue their pushes.

        Returns:
            Number of new notifications (duplicates by the idempotency rules are skipped).
        """
        now = self._now()
        key = dedupe_key(notification_type, event_id, now)
        created = 0
        for chunk in batched(dict.fromkeys(user_ids), FANOUT_BATCH):
            ids = await self._store.add(chunk, notification_type, event_id, key, now)
            if ids:
                await self._jobs.enqueue_push(ids)
                created += len(ids)
        return created


def _payload(
    kind: NotificationType | PushOnlyType,
    target_type: str,
    target_id: UUID,
    notification_id: UUID | None = None,
) -> dict[str, str]:
    """Push data: IDs and the type only (E-04); string values for FCM."""
    data = {"type": kind.value, "targetType": target_type, "targetId": str(target_id)}
    if notification_id is not None:
        data["notificationId"] = str(notification_id)
    return data


class PushNotifications:
    """Push job of one fan-out batch (idempotent: pushed entries are skipped)."""

    def __init__(
        self,
        store: NotificationStore,
        settings: SettingsStore,
        devices: DeviceStore,
        sender: PushSender,
        jobs: PushJobs,
    ) -> None:
        """Create the use case."""
        self._store = store
        self._settings = settings
        self._devices = devices
        self._sender = sender
        self._jobs = jobs

    async def __call__(self, notification_ids: Sequence[UUID]) -> int:
        """Push the notifications whose type the user enabled.

        Returns:
            Number of messages sent.

        Raises:
            PushUnavailableError: The push service is unavailable; the job retries.
        """
        if self._sender.provider is PushProvider.DISABLED:
            return 0
        pending = await self._store.unpushed(notification_ids)
        users = list(dict.fromkeys(n.user_id for n in pending))
        settings = await self._settings.for_users(users)
        wanted = [n for n in pending if settings[n.user_id].pushes(n.type)]
        devices = await self._devices.for_users(
            list(dict.fromkeys(n.user_id for n in wanted)), self._sender.provider
        )
        delivered = [n for n in wanted if devices.get(n.user_id)]
        if not delivered:
            return 0
        badges = await self._store.unread_counts(list(dict.fromkeys(n.user_id for n in delivered)))
        messages = [
            _message(notification, device, badges.get(notification.user_id, 0))
            for notification in delivered
            for device in devices[notification.user_id]
        ]
        result = await self._sender.send(messages)
        if result.invalid_tokens:
            await self._devices.remove_tokens(sorted(result.invalid_tokens))
        if result.receipts:
            await self._jobs.enqueue_receipt_check(result.receipts)
        await self._store.mark_pushed([n.id for n in delivered])
        return len(messages)


def _message(notification: StoredNotification, device: Device, badge: int) -> PushMessage:
    text = PUSH_TEXTS[notification.type]
    return PushMessage(
        token=device.token,
        platform=device.platform,
        title=text.title,
        body=text.body,
        badge=badge,
        data=_payload(notification.type, "event", notification.event_id, notification.id),
    )


class PushToModerator:
    """Push the result of an AI search to the moderator who started it (E-12).

    Push only, no list entry; always on (R11-US4).
    """

    def __init__(
        self, owners: AiSearchOwners, devices: DeviceStore, sender: PushSender, jobs: PushJobs
    ) -> None:
        """Create the use case."""
        self._owners = owners
        self._devices = devices
        self._sender = sender
        self._jobs = jobs

    async def __call__(self, job_id: UUID, kind: PushOnlyType) -> int:
        """Send the push; returns the number of messages.

        Raises:
            PushUnavailableError: The push service is unavailable.
        """
        if self._sender.provider is PushProvider.DISABLED:
            return 0
        moderator = await self._owners.moderator_of(job_id)
        if moderator is None:
            return 0
        devices = (await self._devices.for_users([moderator], self._sender.provider)).get(
            moderator, []
        )
        text = PUSH_TEXTS[kind]
        messages = [
            PushMessage(
                token=device.token,
                platform=device.platform,
                title=text.title,
                body=text.body,
                badge=None,
                data=_payload(kind, "aiSearch", job_id),
            )
            for device in devices
        ]
        if not messages:
            return 0
        result = await self._sender.send(messages)
        if result.invalid_tokens:
            await self._devices.remove_tokens(sorted(result.invalid_tokens))
        if result.receipts:
            await self._jobs.enqueue_receipt_check(result.receipts)
        return len(messages)


class CheckPushReceipts:
    """Remove tokens that turned out invalid after sending (Expo receipts)."""

    def __init__(self, sender: PushSender, devices: DeviceStore) -> None:
        """Create the use case."""
        self._sender = sender
        self._devices = devices

    async def __call__(self, receipts: dict[str, str]) -> int:
        """Check the receipts; returns the number of removed tokens."""
        invalid = await self._sender.check_receipts(receipts)
        if invalid:
            await self._devices.remove_tokens(sorted(invalid))
        return len(invalid)


_AI_PUSHES = {
    AiSearchEventType.COMPLETED.value: PushOnlyType.AI_SEARCH_COMPLETED,
    AiSearchEventType.FAILED.value: PushOnlyType.AI_SEARCH_FAILED,
}


class NotifyForDomainEvent:
    """Consumer of domain events: `near`, `change`, `cancel` and the moderator push (R11-US4)."""

    def __init__(
        self, recipients: Recipients, notify: Notify, push_to_moderator: PushToModerator
    ) -> None:
        """Create the use case."""
        self._recipients = recipients
        self._notify = notify
        self._push_to_moderator = push_to_moderator

    async def __call__(self, event_type: str, payload: Mapping[str, object]) -> int:
        """React to one domain event; other types are ignored.

        Returns:
            Number of new notifications or moderator pushes.
        """
        if event_type in _AI_PUSHES:
            return await self._push_to_moderator(
                UUID(str(payload["jobId"])), _AI_PUSHES[event_type]
            )
        if "eventId" not in payload:
            return 0
        event_id = UUID(str(payload["eventId"]))
        match event_type:
            case DomainEventType.PUBLISHED.value if payload.get("firstPublication"):
                users = await self._recipients.near_home(event_id)
                return await self._notify(NotificationType.NEAR, event_id, users)
            case DomainEventType.UPDATED.value if is_relevant_change(
                [str(name) for name in _list(payload.get("changedFields"))]
            ):
                users = await self._recipients.favorite_holders(event_id)
                return await self._notify(NotificationType.CHANGE, event_id, users)
            case DomainEventType.CANCELLED.value:
                users = await self._recipients.favorite_holders(event_id)
                return await self._notify(NotificationType.CANCEL, event_id, users)
        return 0


def _list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


class SendReminders:
    """Daily at 09:00 Europe/Berlin: favorites that start in `remindDaysBefore` days."""

    def __init__(self, recipients: Recipients, notify: Notify, clock: Clock) -> None:
        """Create the use case."""
        self._recipients = recipients
        self._notify = notify
        self._clock = clock

    async def __call__(self) -> int:
        """Create the reminders; returns the number of new notifications."""
        created = 0
        for event_id, users in (await self._recipients.reminders(self._clock.today())).items():
            created += await self._notify(NotificationType.REMIND, event_id, users)
        return created


@dataclass(frozen=True, slots=True)
class PurgeResult:
    """Numbers of deleted rows."""

    notifications: int
    devices: int


class PurgeNotifications:
    """Daily: notifications after 12 months, devices after 90 days without activity."""

    def __init__(self, store: NotificationStore, devices: DeviceStore, now: Now = _utc_now) -> None:
        """Create the use case."""
        self._store = store
        self._devices = devices
        self._now = now

    async def __call__(self) -> PurgeResult:
        """Delete expired rows."""
        now = self._now()
        return PurgeResult(
            notifications=await self._store.purge(now - RETENTION),
            devices=await self._devices.purge_inactive(now - DEVICE_IDLE),
        )
