"""arq worker entry point: `python -m stadtfest.bootstrap.worker`."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from arq import cron, run_worker
from arq.connections import RedisSettings

from stadtfest.adapters.inbound.worker.jobs import (
    IDP_DELETION_MAX_TRIES,
    JOBS,
    compact_ai_search_logs,
    fail_stuck_searches,
    purge_images,
    purge_invitations,
    purge_notifications,
    purge_outbox,
    run_outbox_relay,
    send_reminders,
)
from stadtfest.application.moderation.image_ports import StorageUnavailableError
from stadtfest.bootstrap.container import Container
from stadtfest.bootstrap.logging import configure_logging
from stadtfest.bootstrap.settings import Settings, get_settings

TIMEZONE = ZoneInfo("Europe/Berlin")


def build_worker_settings(settings: Settings) -> type:
    """Create the arq `WorkerSettings` class for the given settings.

    Args:
        settings: Validated application settings.

    Returns:
        A class usable with `arq.run_worker`.
    """

    async def on_startup(ctx: dict[str, Any]) -> None:
        configure_logging(settings)
        container = Container.build(settings)
        ctx["container"] = container
        if not settings.is_production:
            # Local stack and tests: create the bucket on first start (prod: provisioned).
            with contextlib.suppress(StorageUnavailableError):
                await container.storage.ensure_bucket()
        # Outbox relay (ADR 0005) as background task of the worker process.
        ctx["relay"] = asyncio.create_task(run_outbox_relay(container.relay_outbox))

    async def on_shutdown(ctx: dict[str, Any]) -> None:
        relay: asyncio.Task[None] = ctx["relay"]
        relay.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await relay
        container: Container = ctx["container"]
        await container.aclose()

    class WorkerSettings:
        functions: ClassVar[list[Callable[..., Awaitable[object]]]] = list(JOBS)
        cron_jobs: ClassVar[list[Any]] = [
            cron(purge_outbox, hour={3}, minute={30}, unique=True),
            cron(purge_images, hour={3}, minute={45}, unique=True),
            cron(fail_stuck_searches, minute={0, 10, 20, 30, 40, 50}, unique=True),
            cron(compact_ai_search_logs, weekday="sun", hour={4}, minute={15}, unique=True),
            cron(purge_notifications, hour={3}, minute={50}, unique=True),
            cron(purge_invitations, hour={3}, minute={55}, unique=True),
            cron(send_reminders, hour={9}, minute={0}, unique=True),
        ]
        redis_settings = RedisSettings.from_dsn(str(settings.redis_url))
        timezone = TIMEZONE
        max_jobs = 10
        job_timeout = 600
        max_tries = IDP_DELETION_MAX_TRIES

    WorkerSettings.on_startup = on_startup  # type: ignore[attr-defined]
    WorkerSettings.on_shutdown = on_shutdown  # type: ignore[attr-defined]
    return WorkerSettings


def main() -> None:
    """Run the worker until interrupted."""
    run_worker(build_worker_settings(get_settings()))


if __name__ == "__main__":
    main()
