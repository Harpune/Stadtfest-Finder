import pytest
from arq import create_pool
from arq.connections import RedisSettings
from arq.constants import default_queue_name, health_check_key_suffix
from arq.worker import Worker, async_check_health

from stadtfest.bootstrap.settings import Settings
from stadtfest.bootstrap.worker import build_worker_settings

pytestmark = pytest.mark.integration


async def test_enqueued_ping_job_is_executed(integration_settings: Settings) -> None:
    redis = await create_pool(RedisSettings.from_dsn(str(integration_settings.redis_url)))
    job = await redis.enqueue_job("ping")
    assert job is not None

    worker_settings = build_worker_settings(integration_settings)
    worker = Worker(
        functions=worker_settings.functions,
        redis_pool=redis,
        on_startup=worker_settings.on_startup,
        on_shutdown=worker_settings.on_shutdown,
        burst=True,
        poll_delay=0.1,
    )
    await worker.main()
    await worker.close()

    assert await job.result(timeout=5) == "pong"
    await redis.aclose()


async def test_health_check_reports_a_running_worker(integration_settings: Settings) -> None:
    redis_settings = RedisSettings.from_dsn(str(integration_settings.redis_url))
    redis = await create_pool(redis_settings)
    await redis.delete(default_queue_name + health_check_key_suffix)
    assert await async_check_health(redis_settings) == 1

    worker_settings = build_worker_settings(integration_settings)
    worker = Worker(
        functions=worker_settings.functions,
        redis_pool=redis,
        on_startup=worker_settings.on_startup,
        on_shutdown=worker_settings.on_shutdown,
        health_check_interval=worker_settings.health_check_interval,
        burst=True,
        poll_delay=0.1,
    )
    await worker.main()

    # `python -m stadtfest.bootstrap.worker --check` (container healthcheck) reads this key.
    assert await async_check_health(redis_settings) == 0
    ttl = await redis.ttl(default_queue_name + health_check_key_suffix)
    assert 0 < ttl <= worker_settings.health_check_interval + 1
    await worker.close()  # a stopped worker removes its key
    assert await async_check_health(redis_settings) == 1
    await redis.aclose()
