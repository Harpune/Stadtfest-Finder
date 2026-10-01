"""arq worker entry point: `python -m stadtfest.bootstrap.worker`."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from arq import run_worker
from arq.connections import RedisSettings

from stadtfest.adapters.inbound.worker.jobs import IDP_DELETION_MAX_TRIES, JOBS
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
        ctx["container"] = Container.build(settings)

    async def on_shutdown(ctx: dict[str, Any]) -> None:
        container: Container = ctx["container"]
        await container.aclose()

    class WorkerSettings:
        functions: ClassVar[list[Callable[..., Awaitable[object]]]] = list(JOBS)
        cron_jobs: ClassVar[list[Any]] = []  # scheduled jobs start with R11
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
