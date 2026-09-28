"""Health endpoints (`/v1/health/*`), see api/openapi.yaml tag `health`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from stadtfest.application.health.check_readiness import CheckReadiness
from stadtfest.generated.models import HealthStatus, ReadinessStatus

router = APIRouter(prefix="/v1/health", tags=["health"])


def get_check_readiness(request: Request) -> CheckReadiness:
    """Resolve the readiness use case wired in the composition root."""
    use_case: CheckReadiness = request.app.state.check_readiness
    return use_case


@router.get("/live", operation_id="getLiveness", response_model=HealthStatus)
async def get_liveness() -> HealthStatus:
    """Liveness probe: the process can serve requests."""
    return HealthStatus(status="ok")


@router.get(
    "/ready",
    operation_id="getReadiness",
    response_model=ReadinessStatus,
    responses={503: {"model": ReadinessStatus}},
)
async def get_readiness(
    check_readiness: Annotated[CheckReadiness, Depends(get_check_readiness)],
) -> JSONResponse:
    """Readiness probe: all dependencies are reachable."""
    readiness = await check_readiness()
    body = ReadinessStatus(
        status="ok" if readiness.ready else "unavailable",
        checks={name: "ok" if ok else "unavailable" for name, ok in readiness.checks.items()},
    )
    return JSONResponse(status_code=200 if readiness.ready else 503, content=body.model_dump())
