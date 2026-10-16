"""arq worker entry point: `python -m stadtfest.bootstrap.worker [--check]`."""

from __future__ import annotations

import asyncio
import contextlib
import sys
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from arq import cron, run_worker
from arq.connections import RedisSettings
from arq.worker import check_health

from stadtfest.adapters.inbound.worker.jobs import (
    IDP_DELETION_MAX_TRIES,
    JOBS,
    compact_ai_search_logs,
    fail_stuck_searches,
    purge_images,
    purge_invitations,
    purge_notifications,
    purge_outbox,
    report_outbox_backlog,
    run_outbox_relay,
    send_reminders,
)
from stadtfest.application.moderation.image_ports import StorageUnavailableError
from stadtfest.bootstrap.container import Container
from stadtfest.bootstrap.logging import configure_logging
from stadtfest.bootstrap.settings import Settings, get_settings

TIMEZONE = ZoneInfo("Europe/Berlin")
HEALTH_CHECK_INTERVAL_SECONDS = 60


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
        # After a failed startup the keys are missing; do not hide the original error.
        relay: asyncio.Task[None] | None = ctx.get("relay")
        if relay is not None:
            relay.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await relay
        container: Container | None = ctx.get("container")
        if container is not None:
            await container.aclose()

    class WorkerSettings:
        functions: ClassVar[list[Callable[..., Awaitable[object]]]] = list(JOBS)
        cron_jobs: ClassVar[list[Any]] = [
            cron(purge_outbox, hour={3}, minute={30}, unique=True),
            cron(purge_images, hour={3}, minute={45}, unique=True),
            cron(fail_stuck_searches, minute={0, 10, 20, 30, 40, 50}, unique=True),
            cron(report_outbox_backlog, minute=set(range(0, 60, 5)), unique=True),
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
        # The health key expires after this interval; `--check` (container healthcheck) reads it.
        health_check_interval = HEALTH_CHECK_INTERVAL_SECONDS

    WorkerSettings.on_startup = on_startup  # type: ignore[attr-defined]
    WorkerSettings.on_shutdown = on_shutdown  # type: ignore[attr-defined]
    return WorkerSettings


def main(argv: list[str] | None = None) -> int:
    """Run the worker until interrupted, or check a running worker with `--check`.

    Args:
        argv: Command line arguments without the program name (default: `sys.argv[1:]`).

    Returns:
        The exit code; with `--check` 0 if a worker reported healthy within the last minute.
    """
    args = sys.argv[1:] if argv is None else argv
    if args not in ([], ["--check"]):
        print("usage: python -m stadtfest.bootstrap.worker [--check]", file=sys.stderr)
        return 2
    worker_settings = build_worker_settings(get_settings())
    if args:
        return check_health(worker_settings)
    run_worker(worker_settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
