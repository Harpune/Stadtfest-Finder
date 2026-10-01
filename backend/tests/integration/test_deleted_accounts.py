"""Redis register of deleted accounts against a real Redis (Testcontainers)."""

import hashlib

import pytest
from redis.asyncio import Redis

from stadtfest.adapters.outbound.cache.deleted_accounts import RedisDeletedAccounts
from stadtfest.application.identity.ports import DeletedAccountsUnavailableError

pytestmark = pytest.mark.integration


async def test_marked_subject_is_deleted_until_the_ttl_ends(redis_url: str) -> None:
    client = Redis.from_url(redis_url, decode_responses=True)
    register = RedisDeletedAccounts(client)
    try:
        await register.mark_deleted("sub-1", ttl_seconds=60)

        assert await register.is_deleted("sub-1")
        assert not await register.is_deleted("sub-2")
        # Only a hash of the subject is stored, with the requested lifetime.
        key = "sf:deleted:" + hashlib.sha256(b"sub-1").hexdigest()
        assert 0 < await client.ttl(key) <= 60
        assert not await client.keys("*sub-1*")
    finally:
        await client.aclose()


async def test_unreachable_redis_raises_the_port_error() -> None:
    client = Redis.from_url("redis://127.0.0.1:1/0", socket_connect_timeout=0.5)
    register = RedisDeletedAccounts(client)
    try:
        with pytest.raises(DeletedAccountsUnavailableError):
            await register.is_deleted("sub-1")
        with pytest.raises(DeletedAccountsUnavailableError):
            await register.mark_deleted("sub-1", ttl_seconds=60)
    finally:
        await client.aclose()
