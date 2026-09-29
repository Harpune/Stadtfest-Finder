"""arq job handlers. Handlers are thin: parse arguments, call a use case, return."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from arq import Retry

from stadtfest.application.identity.ports import IdpUnavailableError
from stadtfest.application.identity.use_cases import DeleteIdpUser

logger = logging.getLogger(__name__)

# Retries of the IdP deletion: 1, 2, 4, ... minutes, capped at 6 hours; about 2 days in total.
IDP_DELETION_MAX_TRIES = 15
_IDP_DELETION_MAX_DEFER_SECONDS = 6 * 60 * 60


async def ping(_ctx: dict[str, Any]) -> str:
    """Smoke-test job proving that enqueue -> execution works.

    Args:
        _ctx: arq job context (unused).

    Returns:
        The constant "pong".
    """
    return "pong"


async def delete_idp_user(ctx: dict[str, Any], subject: str) -> None:
    """Delete a user at the IdP after `DeleteAccount` could not reach it (R05-US6).

    Args:
        ctx: arq job context with the container and `job_try`.
        subject: IdP subject of the deleted user.

    Raises:
        Retry: While the IdP is unavailable and tries are left.
    """
    use_case: DeleteIdpUser = ctx["container"].delete_idp_user
    try:
        await use_case(subject)
    except IdpUnavailableError:
        job_try: int = ctx.get("job_try", 1)
        if job_try >= IDP_DELETION_MAX_TRIES:
            # The job ID contains the IdP subject so operators can delete the user manually
            # (runbook 00-docs/40-operations/zitadel.md).
            logger.error("idp_deletion_failed", extra={"job_id": ctx.get("job_id")})
            return
        raise Retry(defer=min(60 * 2 ** (job_try - 1), _IDP_DELETION_MAX_DEFER_SECONDS)) from None


JOBS: list[Callable[..., Awaitable[object]]] = [ping, delete_idp_user]
