"""Enqueue identity jobs in arq (ADR 0004)."""

from __future__ import annotations

from arq.connections import ArqRedis
from redis.exceptions import RedisError

from stadtfest.application.identity.ports import JobQueueUnavailableError

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
