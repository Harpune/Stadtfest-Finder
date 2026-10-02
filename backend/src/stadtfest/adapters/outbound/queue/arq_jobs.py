"""Enqueue jobs in arq (ADR 0004): identity retries and domain events."""

from __future__ import annotations

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
