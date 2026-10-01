"""Redis register of recently deleted accounts (R05-US6).

Keys contain only a SHA-256 hash of the IdP subject and expire with the last access
token of the account, so no personal data is kept beyond the token lifetime.
"""

from __future__ import annotations

import hashlib

from redis.asyncio import Redis
from redis.exceptions import RedisError

from stadtfest.application.identity.ports import DeletedAccountsUnavailableError


class RedisDeletedAccounts:
    """Implements the `DeletedAccounts` port with expiring Redis keys."""

    def __init__(self, client: Redis, prefix: str = "sf:deleted:") -> None:
        """Create the adapter.

        Args:
            client: Redis client.
            prefix: Key prefix to separate these keys.
        """
        self._client = client
        self._prefix = prefix

    def _key(self, subject: str) -> str:
        return self._prefix + hashlib.sha256(subject.encode()).hexdigest()

    async def mark_deleted(self, subject: str, ttl_seconds: int) -> None:
        """Remember the subject as deleted for `ttl_seconds`."""
        try:
            await self._client.set(self._key(subject), "1", ex=ttl_seconds)
        except RedisError:
            raise DeletedAccountsUnavailableError from None

    async def is_deleted(self, subject: str) -> bool:
        """Return True while the subject is marked as deleted."""
        try:
            return bool(await self._client.exists(self._key(subject)))
        except RedisError:
            raise DeletedAccountsUnavailableError from None
