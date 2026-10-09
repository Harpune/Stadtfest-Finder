"""Enqueue jobs in arq (ADR 0004): identity retries, domain events and pushes."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from arq.connections import ArqRedis
from redis.exceptions import RedisError

from stadtfest.application.identity.ports import JobQueueUnavailableError
from stadtfest.application.outbox.ports import OutboxMessage

DELETE_IDP_USER_JOB = "delete_idp_user"


def create_arq_redis(redis_url: str) -> ArqRedis:
    """Create an arq-compatible Redis client (binary responses for pickled jobs).

    Args:
        redis_url: Redis connection URL.

    Returns:
        The client; close it on shutdown.
    """
    client: ArqRedis = ArqRedis.from_url(redis_url)
    return client


class ArqAccountJobs:
    """`AccountJobQueue` backed by arq."""

    def __init__(self, redis: ArqRedis) -> None:
        """Create the adapter.

        Args:
            redis: arq Redis client.
        """
        self._redis = redis

    async def enqueue_idp_deletion(self, subject: str) -> None:
        """Enqueue `delete_idp_user`; the job ID deduplicates repeated requests.

        Raises:
            JobQueueUnavailableError: If Redis cannot be reached.
        """
        try:
            await self._redis.enqueue_job(
                DELETE_IDP_USER_JOB, subject, _job_id=f"{DELETE_IDP_USER_JOB}:{subject}"
            )
        except (RedisError, OSError):
            raise JobQueueUnavailableError from None


HANDLE_DOMAIN_EVENT_JOB = "handle_domain_event"


class ArqEventQueue:
    """`EventQueue` backed by arq: one job per outbox message (ADR 0005)."""

    def __init__(self, redis: ArqRedis) -> None:
        """Create the adapter.

        Args:
            redis: arq Redis client.
        """
        self._redis = redis

    async def enqueue_domain_event(self, message: OutboxMessage) -> None:
        """Enqueue the consumer job; the job ID makes a second relay of the message a no-op."""
        await self._redis.enqueue_job(
            HANDLE_DOMAIN_EVENT_JOB,
            str(message.id),
            message.type,
            message.payload,
            _job_id=f"{HANDLE_DOMAIN_EVENT_JOB}:{message.id}",
        )


PUSH_NOTIFICATIONS_JOB = "push_notifications"
CHECK_PUSH_RECEIPTS_JOB = "check_push_receipts"
# Expo makes receipts available after a few minutes and keeps them for a day.
RECEIPT_DELAY_SECONDS = 15 * 60


class ArqPushJobs:
    """`PushJobs` backed by arq (R11-US3)."""

    def __init__(self, redis: ArqRedis) -> None:
        """Create the adapter.

        Args:
            redis: arq Redis client.
        """
        self._redis = redis

    async def enqueue_push(self, notification_ids: Sequence[UUID]) -> None:
        """One job per fan-out batch; the first ID makes a repeated enqueue a no-op."""
        ids = [str(notification_id) for notification_id in notification_ids]
        await self._redis.enqueue_job(
            PUSH_NOTIFICATIONS_JOB, ids, _job_id=f"{PUSH_NOTIFICATIONS_JOB}:{ids[0]}"
        )

    async def enqueue_receipt_check(self, receipts: dict[str, str]) -> None:
        """Check the Expo receipts after `RECEIPT_DELAY_SECONDS`."""
        await self._redis.enqueue_job(
            CHECK_PUSH_RECEIPTS_JOB, receipts, _defer_by=RECEIPT_DELAY_SECONDS
        )
