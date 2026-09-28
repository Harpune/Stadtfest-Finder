import pytest
from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Worker

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
