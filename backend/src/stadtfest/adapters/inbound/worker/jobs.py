"""arq job handlers. Handlers are thin: parse arguments, call a use case, return."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from arq import Retry

from stadtfest.application.ai_ingestion.use_cases import CompactAiSearchLogs, FailStuckSearches
from stadtfest.application.collections.invitations import PurgeInvitations
from stadtfest.application.identity.ports import IdpUnavailableError
from stadtfest.application.identity.use_cases import DeleteIdpUser
from stadtfest.application.moderation.images import PurgeImages
from stadtfest.application.notifications.ports import PushUnavailableError
from stadtfest.application.notifications.use_cases import (
    CheckPushReceipts,
    PurgeNotifications,
    PushNotifications,
    SendReminders,
)
from stadtfest.application.outbox.ports import OutboxMessage
from stadtfest.application.outbox.use_cases import (
    RELAY_BATCH,
    HandleDomainEvent,
    PurgeOutbox,
    RelayOutbox,
)

logger = logging.getLogger(__name__)

# Retries of the IdP deletion: 1, 2, 4, ... minutes, capped at 6 hours; about 2 days in total.
IDP_DELETION_MAX_TRIES = 15
_IDP_DELETION_MAX_DEFER_SECONDS = 6 * 60 * 60


async def ping(_ctx: dict[str, Any]) -> str:
    """Smoke-test job proving that enqueue -> execution works.

    Args:
        _ctx: arq job context (unused).

    Returns:
        The constant "pong".
    """
    return "pong"


async def delete_idp_user(ctx: dict[str, Any], subject: str) -> None:
    """Delete a user at the IdP after `DeleteAccount` could not reach it (R05-US6).

    Args:
        ctx: arq job context with the container and `job_try`.
        subject: IdP subject of the deleted user.

    Raises:
        Retry: While the IdP is unavailable and tries are left.
    """
    use_case: DeleteIdpUser = ctx["container"].delete_idp_user
    try:
        await use_case(subject)
    except IdpUnavailableError:
        job_try: int = ctx.get("job_try", 1)
        if job_try >= IDP_DELETION_MAX_TRIES:
            # The job ID contains the IdP subject so operators can delete the user manually
            # (runbook 00-docs/40-operations/zitadel.md).
            logger.error("idp_deletion_failed", extra={"job_id": ctx.get("job_id")})
            return
        raise Retry(defer=min(60 * 2 ** (job_try - 1), _IDP_DELETION_MAX_DEFER_SECONDS)) from None


RELAY_INTERVAL_SECONDS = 1.0


async def run_outbox_relay(relay: RelayOutbox, interval: float = RELAY_INTERVAL_SECONDS) -> None:
    """Relay pending domain events until cancelled (polls every second, ADR 0005).

    Runs as a background task of the worker instead of an arq cron job, so it does not log
    one job line per second. A full batch is followed immediately by the next one.

    Args:
        relay: The relay use case.
        interval: Pause when the outbox is empty.
    """
    while True:
        try:
            relayed = await relay()
        except Exception:  # noqa: BLE001  # keep relaying after DB/Redis hiccups
            logger.warning("outbox_relay_failed")
            relayed = 0
        if relayed < RELAY_BATCH:
            await asyncio.sleep(interval)


async def handle_domain_event(
    ctx: dict[str, Any], message_id: str, event_type: str, payload: dict[str, object]
) -> None:
    """Run the consumers of one domain event (idempotent).

    Args:
        ctx: arq job context with the container.
        message_id: Outbox message ID.
        event_type: Event type, e.g. `event.published`.
        payload: IDs and field names of the event.
    """
    use_case: HandleDomainEvent = ctx["container"].handle_domain_event
    await use_case(OutboxMessage(UUID(message_id), event_type, payload))


async def purge_outbox(ctx: dict[str, Any]) -> int:
    """Delete dispatched outbox messages older than 14 days (daily).

    Args:
        ctx: arq job context with the container.

    Returns:
        Number of deleted messages.
    """
    use_case: PurgeOutbox = ctx["container"].purge_outbox
    return await use_case()


async def purge_images(ctx: dict[str, Any]) -> int:
    """Delete stale uploads and images of deleted events (daily, R08-US5).

    Args:
        ctx: arq job context with the container.

    Returns:
        Number of deleted uploads and images.
    """
    use_case: PurgeImages = ctx["container"].purge_images
    result = await use_case()
    return result.uploads + result.images


async def fail_stuck_searches(ctx: dict[str, Any]) -> int:
    """Watchdog: AI searches still queued/running after twice the timeout fail (R10).

    Args:
        ctx: arq job context with the container.

    Returns:
        Number of jobs marked failed.
    """
    use_case: FailStuckSearches = ctx["container"].fail_stuck_searches
    return await use_case()


async def compact_ai_search_logs(ctx: dict[str, Any]) -> int:
    """Weekly: AI search logs older than 90 days keep only their counters (R10).

    Args:
        ctx: arq job context with the container.

    Returns:
        Number of jobs changed.
    """
    use_case: CompactAiSearchLogs = ctx["container"].compact_ai_search_logs
    return await use_case()


# Retries of a push batch while the push service is unavailable: 30 s, 1, 2, 4 min.
PUSH_MAX_TRIES = 5


def _push_retry(ctx: dict[str, Any]) -> Retry | None:
    """The retry for a push job, or None (logged) once the tries are used up."""
    job_try: int = ctx.get("job_try", 1)
    if job_try >= PUSH_MAX_TRIES:
        logger.error("push_failed", extra={"job_id": ctx.get("job_id")})
        return None
    return Retry(defer=30 * 2 ** (job_try - 1))


async def push_notifications(ctx: dict[str, Any], notification_ids: list[str]) -> int:
    """Push one fan-out batch of notifications (R11-US3).

    Args:
        ctx: arq job context with the container.
        notification_ids: IDs of the notifications of the batch.

    Returns:
        Number of messages sent.

    Raises:
        Retry: While the push service is unavailable and tries are left.
    """
    use_case: PushNotifications = ctx["container"].push_notifications
    try:
        return await use_case([UUID(value) for value in notification_ids])
    except PushUnavailableError:
        retry = _push_retry(ctx)
        if retry is None:
            return 0
        raise retry from None


async def check_push_receipts(ctx: dict[str, Any], receipts: dict[str, str]) -> int:
    """Remove tokens that Expo reports as invalid in the receipts (R11-US5).

    Args:
        ctx: arq job context with the container.
        receipts: Ticket ID -> push token.

    Returns:
        Number of removed tokens.

    Raises:
        Retry: While the push service is unavailable and tries are left.
    """
    use_case: CheckPushReceipts = ctx["container"].check_push_receipts
    try:
        return await use_case(receipts)
    except PushUnavailableError:
        retry = _push_retry(ctx)
        if retry is None:
            return 0
        raise retry from None


async def send_reminders(ctx: dict[str, Any]) -> int:
    """Daily 09:00 Europe/Berlin: reminders for favorites that start soon (R11-US4).

    Args:
        ctx: arq job context with the container.

    Returns:
        Number of new notifications.
    """
    use_case: SendReminders = ctx["container"].send_reminders
    return await use_case()


async def purge_invitations(ctx: dict[str, Any]) -> int:
    """Daily: invitations six months after the event ended (Löschkonzept).

    Args:
        ctx: arq job context with the container.

    Returns:
        Number of deleted invitations.
    """
    use_case: PurgeInvitations = ctx["container"].purge_invitations
    return await use_case()


async def purge_notifications(ctx: dict[str, Any]) -> int:
    """Daily: notifications after 12 months, devices after 90 idle days (Löschkonzept).

    Args:
        ctx: arq job context with the container.

    Returns:
        Number of deleted notifications and devices.
    """
    use_case: PurgeNotifications = ctx["container"].purge_notifications
    result = await use_case()
    return result.notifications + result.devices


JOBS: list[Callable[..., Awaitable[object]]] = [
    ping,
    delete_idp_user,
    handle_domain_event,
    purge_outbox,
    purge_images,
    fail_stuck_searches,
    compact_ai_search_logs,
    push_notifications,
    check_push_receipts,
    send_reminders,
    purge_invitations,
    purge_notifications,
]
