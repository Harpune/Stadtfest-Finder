"""Outbound ports of the notifications context (R11)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from stadtfest.domain.identity.principal import Principal
from stadtfest.domain.notifications.notification import EventFacts, NotificationType
from stadtfest.domain.notifications.settings import NotificationSettings


class PushProvider(StrEnum):
    """`PUSH_PROVIDER`: how pushes reach the devices."""

    EXPO = "expo"
    DIRECT = "direct"
    DISABLED = "disabled"


class DevicePlatform(StrEnum):
    """Operating system of a device."""

    IOS = "ios"
    ANDROID = "android"


@dataclass(frozen=True, slots=True)
class StoredNotification:
    """A notification as stored: type and IDs only (E-09)."""

    id: UUID
    user_id: UUID
    type: NotificationType
    event_id: UUID
    read: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ListedNotification:
    """A notification with the current data of its event (for the text)."""

    notification: StoredNotification
    event: EventFacts


@dataclass(frozen=True, slots=True)
class PageCursor:
    """Position after the last notification of a page (newest first)."""

    created_at: datetime
    id: UUID


class NotificationStore(Protocol):
    """Table `notification`."""

    async def add(
        self,
        user_ids: Sequence[UUID],
        notification_type: NotificationType,
        event_id: UUID,
        key: str,
        created_at: datetime,
    ) -> list[UUID]:
        """Insert one unread notification per user unless `(user, key)` exists.

        Returns:
            IDs of the inserted notifications.
        """
        ...

    async def page(
        self, user_id: UUID, after: PageCursor | None, limit: int
    ) -> list[ListedNotification]:
        """Notifications of the user, newest first; those of deleted events are left out."""
        ...

    async def unread_count(self, user_id: UUID) -> int:
        """Unread notifications of the user (without deleted events)."""
        ...

    async def unread_counts(self, user_ids: Sequence[UUID]) -> dict[UUID, int]:
        """Unread notifications per user, for the badge of a push."""
        ...

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> bool:
        """Mark one notification of the user as read; False if it does not exist."""
        ...

    async def mark_all_read(self, user_id: UUID) -> None:
        """Mark all notifications of the user as read."""
        ...

    async def unpushed(self, ids: Sequence[UUID]) -> list[StoredNotification]:
        """The given notifications that were not pushed yet."""
        ...

    async def mark_pushed(self, ids: Sequence[UUID]) -> None:
        """Remember that these notifications were pushed."""
        ...

    async def purge(self, before: datetime) -> int:
        """Delete notifications created before the time; returns the number deleted."""
        ...


class SettingsStore(Protocol):
    """Table `notification_settings`; users without a row have the defaults."""

    async def get(self, user_id: UUID) -> NotificationSettings:
        """Settings of the user, the defaults if none are stored."""
        ...

    async def put(self, user_id: UUID, settings: NotificationSettings) -> None:
        """Store the settings."""
        ...

    async def for_users(self, user_ids: Sequence[UUID]) -> dict[UUID, NotificationSettings]:
        """Settings of all given users (defaults for users without a row)."""
        ...


class Recipients(Protocol):
    """Who is affected by an event (reads favorites and homes)."""

    async def favorite_holders(self, event_id: UUID) -> list[UUID]:
        """Users with the event as favorite."""
        ...

    async def near_home(self, event_id: UUID) -> list[UUID]:
        """Users whose home lies within their own radius around the published event."""
        ...

    async def reminders(self, today: date) -> dict[UUID, list[UUID]]:
        """Event ID -> users whose favorite starts `remind_days_before` days after today.

        Only published events count; users without settings use the default (1 day).
        """
        ...


@dataclass(frozen=True, slots=True)
class Device:
    """A registered push token."""

    token: str
    platform: DevicePlatform
    provider: PushProvider


class DeviceStore(Protocol):
    """Table `device`."""

    async def register(self, user_id: UUID, device: Device, now: datetime) -> None:
        """Insert or update the token; a token of another user moves to this user."""
        ...

    async def remove(self, user_id: UUID, token: str) -> None:
        """Delete the token if it belongs to the user."""
        ...

    async def for_users(
        self, user_ids: Sequence[UUID], provider: PushProvider
    ) -> dict[UUID, list[Device]]:
        """Devices of the users registered for the provider."""
        ...

    async def remove_tokens(self, tokens: Sequence[str]) -> None:
        """Delete tokens the push service reported as invalid."""
        ...

    async def purge_inactive(self, before: datetime) -> int:
        """Delete devices last seen before the time; returns the number deleted."""
        ...


@dataclass(frozen=True, slots=True)
class PushMessage:
    """One push to one device. `data` holds IDs only, all values are strings."""

    token: str
    platform: DevicePlatform
    title: str
    body: str
    badge: int | None
    data: dict[str, str]


@dataclass(frozen=True, slots=True)
class PushResult:
    """Outcome of a send.

    Attributes:
        invalid_tokens: Tokens the service rejected for good (app removed, token expired).
        receipts: Ticket ID -> token, for services that report delivery later (Expo).
    """

    invalid_tokens: frozenset[str] = frozenset()
    receipts: dict[str, str] = field(default_factory=dict)


class PushUnavailableError(Exception):
    """The push service cannot be reached or rejects the credentials; retry later."""


class PushSender(Protocol):
    """Push port (CLAUDE.md "Push notifications"): `expo`, `direct` or `disabled`."""

    provider: PushProvider

    async def send(self, messages: Sequence[PushMessage]) -> PushResult:
        """Send the messages; per-device failures are reported, not raised.

        Raises:
            PushUnavailableError: The service is unavailable as a whole.
        """
        ...

    async def check_receipts(self, receipts: dict[str, str]) -> frozenset[str]:
        """Tokens that turned out to be invalid according to the receipts.

        Raises:
            PushUnavailableError: The service is unavailable as a whole.
        """
        ...


class PushJobs(Protocol):
    """Background jobs of the push delivery (arq)."""

    async def enqueue_push(self, notification_ids: Sequence[UUID]) -> None:
        """Push the notifications in a separate job (fan-out batch)."""
        ...

    async def enqueue_receipt_check(self, receipts: dict[str, str]) -> None:
        """Check the receipts later (Expo makes them available after a few minutes)."""
        ...


class AiSearchOwners(Protocol):
    """Who started an AI search (ai_ingestion context)."""

    async def moderator_of(self, job_id: UUID) -> UUID | None:
        """The moderator's user ID, None if unknown or the account was deleted."""
        ...


class AccountResolver(Protocol):
    """Makes sure the caller has an account (identity context) and returns its ID."""

    async def __call__(self, principal: Principal) -> UUID:
        """Create the account on first use and return the user ID."""
        ...
