"""`/v1/mod/ai-searches`: AI search by postal code (R10, flow C1/C8).

Thin adapter: parse and translate; authorization and rules live in the use cases.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.domain.ai_ingestion.job import AiSearchJob, AiSearchStatus
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/mod/ai-searches", tags=["moderation"])


def _search(job: AiSearchJob) -> api.AiSearch:
    return api.AiSearch(
        id=job.id,
        postal_code=job.postal_code,
        place_name=job.place_name,
        status=api.AiSearchStatus(job.status.value),
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        new_event_ids=list(job.new_event_ids),
        skipped=api.AiSearchSkipped(
            duplicate=job.skipped.duplicate,
            out_of_region=job.skipped.out_of_region,
            invalid=job.skipped.invalid,
            unverified_source=job.skipped.unverified_source,
        ),
        error_code=job.error_code.value if job.error_code else None,
    )


@router.get("", operation_id="listAiSearches", response_model=list[api.AiSearch])
async def list_searches(
    deps: Deps, principal: CurrentPrincipal, status: api.AiSearchStatus | None = None
) -> list[api.AiSearch]:
    """The caller's searches; `running` also returns queued ones."""
    value = status.root if status else None
    active_only = value in {AiSearchStatus.RUNNING.value, AiSearchStatus.QUEUED.value}
    jobs = await deps.list_ai_searches(principal, active_only=active_only)
    if value and not active_only:
        jobs = [job for job in jobs if job.status.value == value]
    return [_search(job) for job in jobs]


@router.post("", operation_id="startAiSearch", status_code=202, response_model=api.AiSearch)
async def start_search(
    deps: Deps, principal: CurrentPrincipal, body: api.AiSearchRequest
) -> api.AiSearch:
    """Queue a search; the worker stores verified finds as drafts."""
    return _search(await deps.start_ai_search(principal, body.postal_code))


@router.get("/{job_id}", operation_id="getAiSearch", response_model=api.AiSearch)
async def get_search(deps: Deps, principal: CurrentPrincipal, job_id: UUID) -> api.AiSearch:
    """Status and result of one of the caller's searches."""
    return _search(await deps.get_ai_search(principal, job_id))
