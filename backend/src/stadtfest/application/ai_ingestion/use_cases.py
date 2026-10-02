"""Use cases of the AI search by postal code (R10, flow C1-C8).

The API only queues a job (`ai_search.requested` via the outbox); the worker runs the
pipeline: geocoding → LLM with web search tool → validation → source check → region check
→ duplicates → drafts. Finds are never published directly.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from stadtfest.application.ai_ingestion.ports import (
    AiSearchRepository,
    DraftCandidate,
    DraftStore,
    EventFinder,
    FinderLimits,
    LlmUnavailableError,
    SearchHit,
    SourceChecker,
    WebSearchPort,
    WebSearchUnavailableError,
)
from stadtfest.application.events.ports import CategoryCatalog
from stadtfest.application.geocoding.ports import GeocodingPort, GeocodingUnavailableError
from stadtfest.application.moderation.ports import AccountResolver, RegionDirectory
from stadtfest.application.shared.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
    TooManyRequestsError,
)
from stadtfest.application.shared.ports import Clock
from stadtfest.domain.ai_ingestion.categories import map_category
from stadtfest.domain.ai_ingestion.finds import DRAFT_SCHEMA_VERSION, FoundEvent, normalize_url
from stadtfest.domain.ai_ingestion.job import (
    AiSearchError,
    AiSearchJob,
    InvalidJobTransitionError,
    SkipCounts,
    SkipReason,
)
from stadtfest.domain.ai_ingestion.prompt import SYSTEM_PROMPT, SearchParameters, build_prompt
from stadtfest.domain.events.geo import GeoPoint, PostalCode
from stadtfest.domain.events.region import Region
from stadtfest.domain.identity.principal import Principal

logger = logging.getLogger(__name__)

SEARCH_RUNNING = "search_running"
OUTSIDE_REGION = "postal_code_outside_region"
DAILY_LIMIT = "daily_limit"
SEARCH_HORIZON_DAYS = 365
LOG_RETENTION = timedelta(days=90)
HITS_PER_QUERY = 10

Now = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class AiSearchSettings:
    """Limits of the AI search (env, validated at startup)."""

    radius_km: int = 25
    daily_limit: int = 10
    max_tool_calls: int = 8
    timeout_seconds: int = 300


async def _moderator(principal: Principal, regions: RegionDirectory) -> tuple[UUID, Region]:
    if not principal.can_moderate or principal.region_key is None:
        raise ForbiddenError
    region = await regions.by_key(principal.region_key)
    if region is None:
        raise ForbiddenError
    return region.id, region.region


class StartAiSearch:
    """Queue a search for a postal code of the caller's region (R10-US1)."""

    def __init__(
        self,
        jobs: AiSearchRepository,
        regions: RegionDirectory,
        accounts: AccountResolver,
        geocoding: GeocodingPort,
        clock: Clock,
        settings: AiSearchSettings,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        self._jobs = jobs
        self._regions = regions
        self._accounts = accounts
        self._geocoding = geocoding
        self._clock = clock
        self._settings = settings
        self._now = now

    async def __call__(self, principal: Principal, postal_code: str) -> AiSearchJob:
        """Create a queued job; the worker picks it up via the outbox.

        Raises:
            InvalidInputError: Not five digits, or outside the caller's region.
            ConflictError: `search_running` with `jobId` if one is queued or running.
            TooManyRequestsError: `daily_limit` reached.
        """
        region_id, region = await _moderator(principal, self._regions)
        code = postal_code.strip()
        if not PostalCode.is_valid(code):
            raise InvalidInputError({"postalCode": "invalid"})
        if not region.contains(code):
            raise InvalidInputError({"postalCode": OUTSIDE_REGION}, OUTSIDE_REGION)
        moderator_id = await self._accounts(principal)
        running = await self._jobs.list_for_moderator(moderator_id, active_only=True, limit=1)
        if running:
            raise ConflictError(SEARCH_RUNNING, {"jobId": str(running[0].id)})
        now = self._now()
        midnight = datetime.combine(self._clock.today(), datetime.min.time(), tzinfo=UTC)
        # The day is the Berlin calendar day; counting from UTC midnight is close enough
        # for a limit and never lets more than `daily_limit` through within 24 hours.
        if await self._jobs.count_created_since(moderator_id, midnight) >= (
            self._settings.daily_limit
        ):
            raise TooManyRequestsError(DAILY_LIMIT)
        job = AiSearchJob(uuid4(), moderator_id, region_id, code, await self._place_name(code), now)
        await self._jobs.add(job)
        return job

    async def _place_name(self, code: str) -> str:
        try:
            places = await self._geocoding.search(code, 1)
        except GeocodingUnavailableError:
            return ""
        return places[0].city if places else ""


class GetAiSearch:
    """Status of one of the caller's searches (R10-US2, polled every 10 s)."""

    def __init__(
        self, jobs: AiSearchRepository, regions: RegionDirectory, accounts: AccountResolver
    ) -> None:
        """Create the use case."""
        self._jobs = jobs
        self._regions = regions
        self._accounts = accounts

    async def __call__(self, principal: Principal, job_id: UUID) -> AiSearchJob:
        """Return the job.

        Raises:
            NotFoundError: Unknown or another moderator's job.
        """
        await _moderator(principal, self._regions)
        job = await self._jobs.get(job_id)
        if job is None or job.moderator_id != await self._accounts(principal):
            raise NotFoundError
        return job


class ListAiSearches:
    """The caller's searches; `active_only` restores the status bar (R10-US2)."""

    def __init__(
        self, jobs: AiSearchRepository, regions: RegionDirectory, accounts: AccountResolver
    ) -> None:
        """Create the use case."""
        self._jobs = jobs
        self._regions = regions
        self._accounts = accounts

    async def __call__(self, principal: Principal, *, active_only: bool) -> list[AiSearchJob]:
        """Return up to 20 jobs, newest first."""
        await _moderator(principal, self._regions)
        return await self._jobs.list_for_moderator(
            await self._accounts(principal), active_only=active_only, limit=20
        )


class _RecordingSearch:
    """The LLM's tool: counts calls and remembers queries and result URLs."""

    def __init__(self, search: WebSearchPort, max_calls: int) -> None:
        self._search = search
        self._max_calls = max_calls
        self.queries: list[str] = []
        self.urls: list[str] = []

    async def __call__(self, query: str) -> list[SearchHit]:
        if len(self.queries) >= self._max_calls:
            return []
        self.queries.append(query)
        hits = await self._search.search(query, HITS_PER_QUERY)
        self.urls.extend(hit.url for hit in hits)
        return hits

    @property
    def normalized_urls(self) -> frozenset[str]:
        return frozenset(normalize_url(url) for url in self.urls)


class RunAiSearch:
    """Worker: the pipeline of one job (R10-US3). Idempotent: only queued jobs run."""

    def __init__(
        self,
        jobs: AiSearchRepository,
        regions: RegionDirectory,
        finder: EventFinder,
        search: WebSearchPort,
        sources: SourceChecker,
        geocoding: GeocodingPort,
        categories: CategoryCatalog,
        drafts: DraftStore,
        clock: Clock,
        settings: AiSearchSettings,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        self._jobs = jobs
        self._regions = regions
        self._finder = finder
        self._search = search
        self._sources = sources
        self._geocoding = geocoding
        self._categories = categories
        self._drafts = drafts
        self._clock = clock
        self._settings = settings
        self._now = now

    async def __call__(self, job_id: UUID) -> AiSearchJob | None:
        """Run the job; returns it finished, or None if there was nothing to do."""
        job = await self._jobs.get(job_id)
        if job is None:
            return None
        try:
            job.start(self._now())
        except InvalidJobTransitionError:
            return None  # delivered twice or already finished
        await self._jobs.save(job)
        started = time.monotonic()
        tool = _RecordingSearch(self._search, self._settings.max_tool_calls)
        log: dict[str, object] = {"schema": DRAFT_SCHEMA_VERSION}
        try:
            async with asyncio.timeout(self._settings.timeout_seconds):
                result = await self._pipeline(job, tool, log)
        except TimeoutError:
            return await self._fail(job, AiSearchError.TIMEOUT, tool, log, started)
        except LlmUnavailableError:
            return await self._fail(job, AiSearchError.LLM_UNAVAILABLE, tool, log, started)
        except WebSearchUnavailableError:
            return await self._fail(job, AiSearchError.SEARCH_UNAVAILABLE, tool, log, started)
        except Exception:  # any other failure ends the job as `internal`
            logger.exception("ai_search_failed", extra={"job_id": str(job.id)})
            return await self._fail(job, AiSearchError.INTERNAL, tool, log, started)
        new_ids, skipped = result
        job.complete(new_ids, skipped, self._log(log, tool, started), self._now())
        await self._jobs.save(job)
        return job

    async def _pipeline(
        self, job: AiSearchJob, tool: _RecordingSearch, log: dict[str, object]
    ) -> tuple[tuple[UUID, ...], SkipCounts]:
        region = await self._region(job)
        today = self._clock.today()
        active = {c.name: c.id for c in await self._categories.list_active()}
        parameters = SearchParameters(
            postal_code=job.postal_code,
            place_name=job.place_name,
            radius_km=self._settings.radius_km,
            date_from=today,
            date_to=today + timedelta(days=SEARCH_HORIZON_DAYS),
            categories=tuple(active),
        )
        result = await self._finder.find(
            SYSTEM_PROMPT,
            build_prompt(parameters),
            tool,
            FinderLimits(max_tool_calls=self._settings.max_tool_calls),
        )
        log["tokens"] = {"input": result.input_tokens, "output": result.output_tokens}
        skipped = SkipCounts(invalid=result.invalid)
        candidates: list[DraftCandidate] = []
        seen_urls: set[str] = set()
        for find in result.finds:
            reason, candidate = await self._check(find, today, tool, region, active)
            normalized = normalize_url(find.source_url)
            if candidate is not None and normalized in seen_urls:
                reason, candidate = SkipReason.DUPLICATE, None
            if candidate is not None and await self._drafts.is_duplicate(
                job.region_id, candidate, normalized
            ):
                reason, candidate = SkipReason.DUPLICATE, None
            if candidate is None:
                skipped = skipped.add(reason or SkipReason.INVALID)
                continue
            seen_urls.add(normalized)
            candidates.append(candidate)
        new_ids = await self._drafts.add_drafts(job.region_id, job.id, self._now(), candidates)
        return tuple(new_ids), skipped

    async def _check(
        self,
        find: FoundEvent,
        today: date,
        tool: _RecordingSearch,
        region: Region,
        active: dict[str, UUID],
    ) -> tuple[SkipReason | None, DraftCandidate | None]:
        if find.problems(today):
            return SkipReason.INVALID, None
        # Only pages the search tool returned in this job count: no invented sources.
        if normalize_url(find.source_url) not in tool.normalized_urls:
            return SkipReason.UNVERIFIED_SOURCE, None
        if not await self._sources.reachable(find.source_url):
            return SkipReason.UNVERIFIED_SOURCE, None
        place = await self._locate(find)
        if place is None:
            return SkipReason.OUT_OF_REGION, None
        location, postal_code, city = place
        if not region.contains(postal_code):
            return SkipReason.OUT_OF_REGION, None
        category = map_category(find.category, active)
        return None, DraftCandidate(find, location, postal_code, city, category)

    async def _locate(self, find: FoundEvent) -> tuple[GeoPoint, str, str] | None:
        """Coordinates (geocoding the address if needed) with ZIP code and city."""
        try:
            if find.plausible_location and find.lat is not None and find.lon is not None:
                location = GeoPoint(find.lat, find.lon)
            else:
                places = await self._geocoding.search(find.address or find.place, 1)
                if not places:
                    return None
                location = places[0].location
            place = await self._geocoding.reverse(location)
        except GeocodingUnavailableError:
            return None
        if place is None or not place.postal_code:
            return None
        return location, place.postal_code, place.city

    async def _region(self, job: AiSearchJob) -> Region:
        found = await self._regions.by_id(job.region_id)
        if found is None:
            raise RuntimeError("region of the job vanished")
        return found.region

    def _log(
        self, log: dict[str, object], tool: _RecordingSearch, started: float
    ) -> dict[str, object]:
        return log | {
            "queries": tool.queries,
            "urls": tool.urls,
            "durationSeconds": round(time.monotonic() - started, 1),
        }

    async def _fail(
        self,
        job: AiSearchJob,
        error: AiSearchError,
        tool: _RecordingSearch,
        log: dict[str, object],
        started: float,
    ) -> AiSearchJob:
        logger.warning("ai_search_job_failed", extra={"error_code": error.value})
        job.fail(error, self._log(log, tool, started), self._now())
        await self._jobs.save(job)
        return job


class FailStuckSearches:
    """Watchdog: jobs still queued/running after twice the timeout failed (worker crash)."""

    def __init__(
        self, jobs: AiSearchRepository, settings: AiSearchSettings, now: Now = _utc_now
    ) -> None:
        """Create the use case."""
        self._jobs = jobs
        self._settings = settings
        self._now = now

    async def __call__(self) -> int:
        """Mark stuck jobs failed (`timeout`); returns their number."""
        limit = self._now() - timedelta(seconds=2 * self._settings.timeout_seconds)
        stuck = await self._jobs.stuck(limit)
        for job in stuck:
            job.fail(AiSearchError.TIMEOUT, job.log, self._now())
            await self._jobs.save(job)
        return len(stuck)


class CompactAiSearchLogs:
    """Weekly: logs older than 90 days keep only their counters (R10, privacy)."""

    def __init__(self, jobs: AiSearchRepository, now: Now = _utc_now) -> None:
        """Create the use case."""
        self._jobs = jobs
        self._now = now

    async def __call__(self) -> int:
        """Compact old logs; returns the number of jobs changed."""
        return await self._jobs.compact_logs(self._now() - LOG_RETENTION)
