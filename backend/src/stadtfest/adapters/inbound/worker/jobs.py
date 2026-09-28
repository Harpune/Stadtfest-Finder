"""arq job handlers. Handlers are thin: parse arguments, call a use case, return."""

from __future__ import annotations

from typing import Any


async def ping(_ctx: dict[str, Any]) -> str:
    """Smoke-test job proving that enqueue -> execution works.

    Args:
        _ctx: arq job context (unused).

    Returns:
        The constant "pong".
    """
    return "pong"


JOBS = [ping]
