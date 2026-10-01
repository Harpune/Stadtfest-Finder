"""arq job handlers. Handlers are thin: parse arguments, call a use case, return."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from arq import Retry

from stadtfest.application.identity.ports import IdpUnavailableError
from stadtfest.application.identity.use_cases import DeleteIdpUser
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


JOBS: list[Callable[..., Awaitable[object]]] = [
    ping,
    delete_idp_user,
    handle_domain_event,
    purge_outbox,
]
