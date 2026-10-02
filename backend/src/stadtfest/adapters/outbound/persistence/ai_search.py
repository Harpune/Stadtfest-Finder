"""PostgreSQL implementation of the AI search ports (R10)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import cast, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.persistence.models import (
    AiSearchJobRow,
    EventRow,
    OutboxRow,
    RejectedSourceRow,
)
from stadtfest.adapters.outbound.persistence.moderation import event_columns
from stadtfest.application.ai_ingestion.ports import DraftCandidate
from stadtfest.domain.ai_ingestion.finds import normalize_url
from stadtfest.domain.ai_ingestion.job import (
    AiSearchError,
    AiSearchEventType,
    AiSearchJob,
    AiSearchStatus,
    SkipCounts,
)
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.maintenance import EventContent, ManagedEvent

# Duplicate rule (R10-US3 step 9).
NAME_SIMILARITY = 0.5
DUPLICATE_DISTANCE_M = 2000
_ACTIVE = (AiSearchStatus.QUEUED.value, AiSearchStatus.RUNNING.value)
# Keys of the log that keep their value when the log is compacted after 90 days.
_COUNTER_KEYS = ("schema", "tokens", "durationSeconds")


def _job(row: AiSearchJobRow) -> AiSearchJob:
    return AiSearchJob(
        id=row.id,
        moderator_id=row.moderator_id,
        region_id=row.region_id,
        postal_code=row.postal_code,
        place_name=row.place_name,
        created_at=row.created_at,
        status=AiSearchStatus(row.status),
        started_at=row.started_at,
        finished_at=row.finished_at,
        new_event_ids=tuple(row.new_event_ids or ()),
        skipped=SkipCounts(
            duplicate=row.skipped_duplicate,
            out_of_region=row.skipped_out_of_region,
            invalid=row.skipped_invalid,
            unverified_source=row.skipped_unverified_source,
        ),
        error_code=AiSearchError(row.error_code) if row.error_code else None,
        log=dict(row.log or {}),
    )


def _values(job: AiSearchJob) -> dict[str, object]:
    return {
        "status": job.status.value,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "new_event_ids": list(job.new_event_ids),
        "skipped_duplicate": job.skipped.duplicate,
        "skipped_out_of_region": job.skipped.out_of_region,
        "skipped_invalid": job.skipped.invalid,
        "skipped_unverified_source": job.skipped.unverified_source,
        "error_code": job.error_code.value if job.error_code else None,
        "log": job.log,
    }


async def _write_event(
    session: AsyncSession, event_type: AiSearchEventType, job: AiSearchJob
) -> None:
    # IDs only: no postal code, no moderator, no content.
    await session.execute(
        insert(OutboxRow),
        [{"id": uuid.uuid4(), "type": event_type.value, "payload": {"jobId": str(job.id)}}],
    )


class SqlAiSearchRepository:
    """Jobs in `ai_search_job`; `ai_search.*` events in the outbox (one transaction)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the repository."""
        self._sessions = sessions

    async def add(self, job: AiSearchJob) -> None:
        """Store a queued job and write `ai_search.requested`."""
        async with self._sessions.begin() as session:
            session.add(
                AiSearchJobRow(
                    id=job.id,
                    moderator_id=job.moderator_id,
                    region_id=job.region_id,
                    postal_code=job.postal_code,
                    place_name=job.place_name,
                    created_at=job.created_at,
                    **_values(job),
                )
            )
            await session.flush()
            await _write_event(session, AiSearchEventType.REQUESTED, job)

    async def get(self, job_id: UUID) -> AiSearchJob | None:
        """One job, or None."""
        async with self._sessions() as session:
            row = await session.get(AiSearchJobRow, job_id)
        return _job(row) if row else None

    async def list_for_moderator(
        self, moderator_id: UUID, *, active_only: bool, limit: int
    ) -> list[AiSearchJob]:
        """The moderator's jobs, newest first."""
        query = select(AiSearchJobRow).where(AiSearchJobRow.moderator_id == moderator_id)
        if active_only:
            query = query.where(AiSearchJobRow.status.in_(_ACTIVE))
        query = query.order_by(AiSearchJobRow.created_at.desc()).limit(limit)
        async with self._sessions() as session:
            return [_job(row) for row in await session.scalars(query)]

    async def count_created_since(self, moderator_id: UUID, since: datetime) -> int:
        """Jobs started since the given time."""
        async with self._sessions() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(AiSearchJobRow)
                .where(
                    AiSearchJobRow.moderator_id == moderator_id,
                    AiSearchJobRow.created_at >= since,
                )
            )
        return int(count or 0)

    async def save(self, job: AiSearchJob) -> None:
        """Store status, result and log; finished jobs write their event."""
        async with self._sessions.begin() as session:
            await session.execute(
                update(AiSearchJobRow).where(AiSearchJobRow.id == job.id).values(**_values(job))
            )
            if job.status is AiSearchStatus.COMPLETED:
                await _write_event(session, AiSearchEventType.COMPLETED, job)
            elif job.status is AiSearchStatus.FAILED:
                await _write_event(session, AiSearchEventType.FAILED, job)

    async def stuck(self, started_before: datetime) -> list[AiSearchJob]:
        """Queued or running jobs created before the given time."""
        async with self._sessions() as session:
            rows = await session.scalars(
                select(AiSearchJobRow).where(
                    AiSearchJobRow.status.in_(_ACTIVE),
                    AiSearchJobRow.created_at < started_before,
                )
            )
            return [_job(row) for row in rows]

    async def compact_logs(self, finished_before: datetime) -> int:
        """Keep only counters in logs of jobs finished before the given time."""
        async with self._sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(AiSearchJobRow).where(
                        AiSearchJobRow.finished_at < finished_before,
                        AiSearchJobRow.log.has_any(["queries", "urls"]),
                    )
                )
            ).all()
            for row in rows:
                row.log = {
                    key: value for key, value in (row.log or {}).items() if key in _COUNTER_KEYS
                }
            return len(rows)


class SqlDraftStore:
    """Duplicate checks against the region's events and new AI drafts (table `event`)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the store."""
        self._sessions = sessions

    async def is_duplicate(
        self, region_id: UUID, candidate: DraftCandidate, normalized_url: str
    ) -> bool:
        """Same source (also rejected ones) or similar name, overlapping dates, < 2 km."""
        find = candidate.find
        point = cast(
            func.ST_SetSRID(
                func.ST_MakePoint(candidate.location.lon, candidate.location.lat), 4326
            ),
            Geography(geometry_type="POINT", srid=4326),
        )
        async with self._sessions() as session:
            rejected = await session.scalar(
                select(RejectedSourceRow.url_normalized).where(
                    RejectedSourceRow.region_id == region_id,
                    RejectedSourceRow.url_normalized == normalized_url,
                )
            )
            if rejected is not None:
                return True
            sources = await session.scalars(
                select(EventRow.source_url).where(
                    EventRow.region_id == region_id,
                    EventRow.source_url.is_not(None),
                    EventRow.deleted_at.is_(None),
                )
            )
            if any(normalize_url(url) == normalized_url for url in sources if url):
                return True
            similar = await session.scalar(
                select(EventRow.id)
                .where(
                    EventRow.region_id == region_id,
                    EventRow.deleted_at.is_(None),
                    func.similarity(func.lower(EventRow.name), find.name.lower())
                    >= NAME_SIMILARITY,
                    EventRow.start_date <= find.date_to,
                    EventRow.end_date >= find.date_from,
                    func.ST_DWithin(EventRow.location, point, DUPLICATE_DISTANCE_M),
                )
                .limit(1)
            )
        return similar is not None

    async def add_drafts(
        self, region_id: UUID, job_id: UUID, found_at: datetime, drafts: Sequence[DraftCandidate]
    ) -> list[UUID]:
        """Store the candidates as drafts (`source = ai`, no audit user)."""
        ids: list[UUID] = []
        async with self._sessions.begin() as session:
            for draft in drafts:
                find = draft.find
                event = ManagedEvent(
                    id=uuid.uuid4(),
                    region_id=region_id,
                    status=EventStatus.DRAFT,
                    content=EventContent(
                        name=find.name,
                        category_id=draft.category_id,
                        start_date=find.date_from,
                        end_date=find.date_to,
                        place=find.place,
                        address=find.address,
                        city=draft.city,
                        postal_code=draft.postal_code,
                        lat=draft.location.lat,
                        lon=draft.location.lon,
                        description=find.description,
                    ).with_defaults(),
                    source="ai",
                    source_url=find.source_url,
                    ai_job_id=job_id,
                    found_at=found_at,
                )
                await session.execute(
                    insert(EventRow).values(
                        id=event.id,
                        version=1,
                        source=event.source,
                        source_url=event.source_url,
                        ai_job_id=event.ai_job_id,
                        found_at=event.found_at,
                        **event_columns(event),
                    )
                )
                ids.append(event.id)
        return ids
