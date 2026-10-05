"""A complete AI search with the fake LLM and search against PostGIS and Redis (R10)."""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.geocoding.fake import FakeGeocoding
from stadtfest.adapters.outbound.llm.fake import FakeEventFinder
from stadtfest.adapters.outbound.persistence.accounts import SqlUserRepository
from stadtfest.adapters.outbound.persistence.ai_search import SqlAiSearchRepository, SqlDraftStore
from stadtfest.adapters.outbound.persistence.catalog import SqlCatalog
from stadtfest.adapters.outbound.persistence.models import EventRow, OutboxRow, RejectedSourceRow
from stadtfest.adapters.outbound.persistence.moderation import (
    SqlManagedEventRepository,
)
from stadtfest.adapters.outbound.search.fake import FakeWebSearch
from stadtfest.adapters.outbound.sources.http import AllowAllSourceChecker
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.ai_ingestion.ports import DraftCandidate
from stadtfest.application.ai_ingestion.use_cases import (
    AiSearchSettings,
    RunAiSearch,
    StartAiSearch,
)
from stadtfest.application.identity.use_cases import EnsureAccount
from stadtfest.domain.ai_ingestion.finds import FoundEvent, normalize_url
from stadtfest.domain.ai_ingestion.job import AiSearchStatus
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.identity.principal import Principal, Role
from tests.integration.seed_support import load

pytestmark = pytest.mark.integration

TODAY = date.today()
MODERATOR = Principal("sub-ai-mod", frozenset({Role.USER, Role.MODERATOR}))


class _Clock:
    def today(self) -> date:
        return TODAY


@pytest.fixture(scope="module")
async def engine(migrated_postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_url)
    await load(async_sessionmaker(engine), TODAY)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _use_cases(
    sessions: async_sessionmaker[AsyncSession],
) -> tuple[StartAiSearch, RunAiSearch, SqlAiSearchRepository]:
    jobs = SqlAiSearchRepository(sessions)
    geocoding = FakeGeocoding()
    settings = AiSearchSettings()
    start = StartAiSearch(
        jobs, EnsureAccount(SqlUserRepository(sessions)), geocoding, _Clock(), settings
    )
    run = RunAiSearch(
        jobs,
        FakeEventFinder(),
        FakeWebSearch(),
        AllowAllSourceChecker(),
        None,
        geocoding,
        SqlCatalog(sessions, ImageUrls("https://img.test/b")),
        SqlDraftStore(sessions),
        _Clock(),
        settings,
    )
    return start, run, jobs


async def test_job_stores_drafts_and_skips_them_the_second_time(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    start, run, jobs = _use_cases(sessions)

    job = await start(MODERATOR, "73430")
    async with sessions() as session:
        requested = await session.scalar(
            select(OutboxRow.type).where(OutboxRow.payload["jobId"].astext == str(job.id))
        )
    assert requested == "ai_search.requested"

    done = await run(job.id)

    assert done is not None
    assert done.status is AiSearchStatus.COMPLETED
    assert len(done.new_event_ids) == 3, done.skipped
    async with sessions() as session:
        drafts = (
            await session.scalars(select(EventRow).where(EventRow.id.in_(done.new_event_ids)))
        ).all()
    assert {d.status for d in drafts} == {"draft"}
    assert {d.source for d in drafts} == {"ai"}
    assert all(d.ai_job_id == job.id and d.source_url and d.found_at for d in drafts)
    lichterfest = next(d for d in drafts if d.name == "Lichterfest Wasseralfingen")
    assert lichterfest.postal_code == "73433"
    stored = await jobs.get(job.id)
    assert stored is not None
    assert stored.log["queries"] == ["Feste Ostalb Herbst"]

    # The same pages again: all three are duplicates now (same sources).
    second = await start(MODERATOR, "73430")
    repeated = await run(second.id)
    assert repeated is not None
    assert (repeated.new_event_ids, repeated.skipped.duplicate) == ((), 3)


async def test_discarded_finds_are_never_suggested_again(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    start, run, _ = _use_cases(sessions)
    principal = Principal(f"sub-{uuid4()}", frozenset({Role.USER, Role.MODERATOR}))
    # Earlier tests may have stored these finds; start from a clean state.
    async with sessions.begin() as session:
        await session.execute(
            update(EventRow)
            .where(EventRow.source == "ai")
            .values(deleted_at=datetime.now(UTC), source_url=None)
        )
    job = await run((await start(principal, "73430")).id)
    assert job is not None
    discarded = job.new_event_ids[0]

    # "Verwerfen" = DELETE in the moderation view (R10-US4).
    repo = SqlManagedEventRepository(sessions)
    event = await repo.get(discarded)
    assert event is not None
    version = event.version
    event.delete()
    await repo.save(event, version, uuid4())
    async with sessions() as session:
        rejected = (await session.scalars(select(RejectedSourceRow.url_normalized))).all()
    assert any("example" in url for url in rejected)

    # Delete the two kept drafts too, so only the rejection prevents a new draft.
    async with sessions.begin() as session:
        await session.execute(
            update(EventRow)
            .where(EventRow.id.in_(job.new_event_ids[1:]))
            .values(deleted_at=datetime.now(UTC), source_url=None)
        )
    again = await run((await start(principal, "73430")).id)
    assert again is not None
    assert len(again.new_event_ids) == 2
    assert again.skipped.duplicate == 1


async def test_one_calendar_page_is_the_source_of_several_events(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """R10b: same page and same name is a duplicate; another name from the page is not."""
    page = f"https://www.bopfingen.de/{uuid4()}/veranstaltungskalender.html"
    store = SqlDraftStore(sessions)

    def candidate(name: str) -> DraftCandidate:
        find = FoundEvent(
            name=name,
            date_from=TODAY,
            date_to=TODAY,
            place="Marktplatz",
            address="Marktplatz, 73441 Bopfingen",
            source_url=page,
        )
        return DraftCandidate(find, GeoPoint(48.857, 10.354), "73441", "Bopfingen", None)

    await store.add_drafts(uuid4(), datetime.now(UTC), [candidate("Heimattage Bopfingen")])
    key = normalize_url(page)

    assert await store.is_duplicate(candidate("Heimattage Bopfingen!"), key)
    assert not await store.is_duplicate(candidate("Weinfest Flochberg"), key)

    async with sessions.begin() as session:
        session.add(RejectedSourceRow(url_normalized=key, name_normalized="weinfest flochberg"))
    assert await store.is_duplicate(candidate("Weinfest Flochberg"), key)
    assert not await store.is_duplicate(candidate("Nikolausmarkt"), key)

    # Rejections from before R10b have no name and still block the whole page.
    async with sessions.begin() as session:
        session.add(RejectedSourceRow(url_normalized=key, name_normalized=""))
    assert await store.is_duplicate(candidate("Nikolausmarkt"), key)
