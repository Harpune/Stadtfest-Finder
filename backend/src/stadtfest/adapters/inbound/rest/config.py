"""`/v1/config`: public app configuration (R11-US5)."""

from __future__ import annotations

from fastapi import APIRouter

from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/config", tags=["config"])


@router.get("", operation_id="getConfig", response_model=api.AppConfig)
async def get_config(deps: Deps) -> api.AppConfig:
    """Return which push token type the app registers."""
    return api.AppConfig(push_provider=api.PushProvider(deps.push_provider.value))
