from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from stadtfest.application.ai_ingestion.ports import SearchHit
from stadtfest.application.ai_ingestion.prompts import load_bundled
from stadtfest.application.ai_ingestion.use_cases import (
    AiSearchSettings,
    CompactAiSearchLogs,
    FailStuckSearches,
    GetAiSearch,
    ListAiSearches,
    RunAiSearch,
    StartAiSearch,
)
from stadtfest.application.events.views import CategoryView
from stadtfest.application.geocoding.ports import Place, PlaceKind
from stadtfest.application.shared.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
    ServiceUnavailableError,
    TooManyRequestsError,
)
from stadtfest.domain.ai_ingestion.finds import FoundEvent
from stadtfest.domain.ai_ingestion.job import AiSearchError, AiSearchStatus
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import (
    FakeAccountResolver,
    FakeAiSearchRepository,
    FakeDraftStore,
    FakeEventFinder,
    FakeGeocoding,
    FakeSourceChecker,
    FakeWebSearch,
    FixedClock,
)

TODAY = date(2026, 10, 2)
NOW = datetime(2026, 10, 2, 9, tzinfo=UTC)
MODERATOR = Principal("sub-mod", frozenset({Role.USER, Role.MODERATOR}))
OTHER = Principal("sub-other", frozenset({Role.USER, Role.MODERATOR}))
USER = Principal("sub-user", frozenset({Role.USER}))
STADTFEST = CategoryView(uuid4(), "Stadtfest", "🎪", "#FFB547", 0)
AALEN = Place("73430 Aalen", "Aalen", GeoPoint(48.8375, 10.0933), PlaceKind.POSTCODE, "73430")
WASSERALFINGEN = Place(
    "73433 Aalen", "Aalen", GeoPoint(48.8623, 10.1019), PlaceKind.POSTCODE, "73433"
)
ULM = Place("89073 Ulm", "Ulm", GeoPoint(48.3984, 9.9916), PlaceKind.POSTCODE, "89073")
SOURCE = "https://www.aalen.de/stadtfest"


class _Catalog:
    async def list_active(self) -> list[CategoryView]:
        return [STADTFEST]


def _find(**changes: object) -> FoundEvent:
    values: dict[str, object] = {
        "name": "Aalener Stadtfest",
        "date_from": date(2026, 10, 17),
        "date_to": date(2026, 10, 18),
        "place": "Marktplatz",
        "address": "Marktplatz 1, 73430 Aalen",
        "source_url": SOURCE,
        "lat": 48.8368,
        "lon": 10.0932,
        "category": "Stadtfest",
    }
    return FoundEvent(**(values | changes))  # type: ignore[arg-type]


class Setup:
    def __init__(self, daily_limit: int = 3, prompt: str = "v2") -> None:
        self.jobs = FakeAiSearchRepository()
        accounts = FakeAccountResolver()
        self.geocoding = FakeGeocoding(places=[AALEN, WASSERALFINGEN, ULM], reverse_result=AALEN)
        self.search = FakeWebSearch(hits=[SearchHit(SOURCE, "Stadtfest Aalen")])
        self.finder = FakeEventFinder(finds=[_find()])
        self.sources = FakeSourceChecker()
        self.drafts = FakeDraftStore()
        self.settings = AiSearchSettings(
            daily_limit=daily_limit, timeout_seconds=1, prompt=load_bundled(prompt)
        )
        clock = FixedClock(TODAY)
        self.start = StartAiSearch(
            self.jobs, accounts, self.geocoding, clock, self.settings, now=lambda: NOW
        )
        self.get = GetAiSearch(self.jobs, accounts)
        self.list = ListAiSearches(self.jobs, accounts)
        self.run = RunAiSearch(
            self.jobs,
            self.finder,
            self.search,
            self.sources,
            self.geocoding,
            _Catalog(),
            self.drafts,
            clock,
            self.settings,
            now=lambda: NOW,
        )


@pytest.fixture
def s() -> Setup:
    return Setup()


# --- start (R10-US1) -----------------------------------------------------------------------


async def test_start_queues_a_job_with_the_place_name(s: Setup) -> None:
    job = await s.start(MODERATOR, "73430")

    assert (job.status, job.postal_code, job.place_name) == (
        AiSearchStatus.QUEUED,
        "73430",
        "Aalen",
    )
    assert s.jobs.outbox == ["ai_search.requested"]


async def test_start_rules(s: Setup) -> None:
    with pytest.raises(ForbiddenError):
        await s.start(USER, "73430")
    with pytest.raises(InvalidInputError):
        await s.start(MODERATOR, "7343")
    with pytest.raises(InvalidInputError) as unknown:
        await s.start(MODERATOR, "99999")
    assert unknown.value.code == "postal_code_unknown"
    s.geocoding.unavailable = True
    with pytest.raises(ServiceUnavailableError):
        await s.start(MODERATOR, "73430")


async def test_any_known_postal_code_can_be_searched(s: Setup) -> None:
    """No regions (ADR 0015): Ulm is as searchable as Aalen."""
    job = await s.start(MODERATOR, "89073")
    assert (job.postal_code, job.place_name) == ("89073", "Ulm")


async def test_one_running_search_per_moderator(s: Setup) -> None:
    first = await s.start(MODERATOR, "73430")
    with pytest.raises(ConflictError) as error:
        await s.start(MODERATOR, "73433")
    assert (error.value.code, error.value.fields) == ("search_running", {"jobId": str(first.id)})
    await s.start(OTHER, "73433")  # other moderators are not blocked


async def test_daily_limit(s: Setup) -> None:
    for _ in range(3):
        job = await s.start(MODERATOR, "73430")
        await s.run(job.id)
    with pytest.raises(TooManyRequestsError):
        await s.start(MODERATOR, "73430")


async def test_daily_limit_zero_stops_the_ai_search() -> None:
    with pytest.raises(TooManyRequestsError):
        await Setup(daily_limit=0).start(MODERATOR, "73430")


async def test_jobs_are_private_to_their_moderator(s: Setup) -> None:
    job = await s.start(MODERATOR, "73430")
    assert (await s.get(MODERATOR, job.id)).id == job.id
    assert [j.id for j in await s.list(MODERATOR, active_only=True)] == [job.id]
    with pytest.raises(NotFoundError):
        await s.get(OTHER, job.id)


# --- pipeline (R10-US3) ----------------------------------------------------------------------


async def test_pipeline_stores_verified_finds_as_drafts(s: Setup) -> None:
    job = await s.start(MODERATOR, "73430")

    done = await s.run(job.id)

    assert done is not None
    assert done.status is AiSearchStatus.COMPLETED
    assert len(done.new_event_ids) == 1
    stored = s.drafts.stored[0]
    assert (stored.postal_code, stored.category_id) == ("73430", STADTFEST.id)
    assert done.log["queries"] == ["Feste 73430"]
    assert done.log["urls"] == [SOURCE]
    assert s.jobs.outbox[-1] == "ai_search.completed"
    assert await s.run(job.id) is None  # delivered twice: nothing happens


async def test_prompt_has_only_public_parameters(s: Setup) -> None:
    job = await s.start(MODERATOR, "73430")
    await s.run(job.id)

    _, prompt = s.finder.prompts[0]
    assert "73430 Aalen" in prompt
    assert "Stadtfest" in prompt
    for private in ("sub-mod", str(job.moderator_id)):
        assert private not in prompt


async def test_prompt_names_the_towns_around_and_is_logged(s: Setup) -> None:
    """v2: towns within the radius from reverse geocoding (public names, deduplicated)."""
    s.geocoding.reverse_result = WASSERALFINGEN
    job = await s.start(MODERATOR, "73430")

    done = await s.run(job.id)

    system, prompt = s.finder.prompts[0]
    assert "Orte im Umkreis: Aalen." in prompt  # Wasseralfingen is a district of Aalen
    assert "Ort für Ort" in system
    assert done is not None
    assert done.log["prompt"] == "v2"
    assert done.log["nearbyPlaces"] == ["Aalen"]
    assert len(s.geocoding.reverse_calls) == 17 + 1  # center + 6 + 10 points, + the find


async def test_other_towns_are_added_and_geocoding_failures_ignored(s: Setup) -> None:
    s.geocoding.reverse_result = ULM
    job = await s.start(MODERATOR, "73430")
    await s.run(job.id)
    assert "Orte im Umkreis: Aalen, Ulm." in s.finder.prompts[0][1]


async def test_prompt_version_comes_from_the_settings() -> None:
    s = Setup(prompt="v1")
    job = await s.start(MODERATOR, "73430")
    done = await s.run(job.id)
    assert done is not None
    assert done.log["prompt"] == "v1"
    assert "Orte im Umkreis" not in s.finder.prompts[0][1]


async def test_no_draft_without_a_verified_source(s: Setup) -> None:
    """DoD: sources the search tool never returned, or dead pages, are rejected."""
    s.finder.finds = [
        _find(source_url="https://invented.example/fest"),
        _find(name="Zweites Fest", source_url="https://www.aalen.de/stadtfest/"),
    ]
    s.sources.dead = {"https://www.aalen.de/stadtfest/"}
    job = await s.start(MODERATOR, "73430")

    done = await s.run(job.id)

    assert done is not None
    assert done.new_event_ids == ()
    assert done.skipped.unverified_source == 2
    assert s.drafts.stored == []


async def test_invalid_out_of_area_and_duplicate_finds_are_counted(s: Setup) -> None:
    s.finder.invalid = 2
    s.finder.finds = [
        _find(date_from=date(2026, 9, 1), date_to=date(2026, 9, 2)),  # past
        _find(name="Bekanntes Fest"),
        _find(name="Doppelt im Lauf"),
        _find(name="Doppelt im Lauf"),
    ]
    s.drafts.known_names = {"Bekanntes Fest"}
    job = await s.start(MODERATOR, "73430")
    done = await s.run(job.id)
    assert done is not None
    assert (done.skipped.invalid, done.skipped.duplicate) == (3, 2)
    assert len(done.new_event_ids) == 1

    # Ulm is ~50 km from Aalen: outside the 25 km radius (+10 %) of the search.
    s.geocoding.reverse_result = ULM
    s.finder.finds = [_find(name="Ulmer Fest", lat=48.3984, lon=9.9916)]
    second = await s.start(OTHER, "73430")
    done = await s.run(second.id)
    assert done is not None
    assert done.skipped.out_of_area == 1


async def test_implausible_coordinates_are_geocoded_again(s: Setup) -> None:
    s.finder.finds = [_find(lat=0.0, lon=0.0)]
    job = await s.start(MODERATOR, "73430")
    await s.run(job.id)

    assert s.drafts.stored[0].location == AALEN.location
    assert s.geocoding.search_calls[-1] == "Marktplatz 1, 73430 Aalen"


async def test_uncertain_category_stays_empty(s: Setup) -> None:
    s.finder.finds = [_find(category="Konzert")]
    job = await s.start(MODERATOR, "73430")
    await s.run(job.id)
    assert s.drafts.stored[0].category_id is None


@pytest.mark.parametrize(
    ("break_it", "code"),
    [("llm", AiSearchError.LLM_UNAVAILABLE), ("search", AiSearchError.SEARCH_UNAVAILABLE)],
)
async def test_provider_failures_fail_the_job(s: Setup, break_it: str, code: AiSearchError) -> None:
    if break_it == "llm":
        s.finder.unavailable = True
    else:
        s.search.unavailable = True
    job = await s.start(MODERATOR, "73430")

    done = await s.run(job.id)

    assert done is not None
    assert (done.status, done.error_code) == (AiSearchStatus.FAILED, code)
    assert s.jobs.outbox[-1] == "ai_search.failed"


async def test_timeout_fails_the_job(s: Setup) -> None:
    s.finder.delay_seconds = 2
    job = await s.start(MODERATOR, "73430")

    done = await s.run(job.id)

    assert done is not None
    assert done.error_code is AiSearchError.TIMEOUT


# --- watchdog and log retention -----------------------------------------------------------


async def test_watchdog_fails_stuck_jobs(s: Setup) -> None:
    job = await s.start(MODERATOR, "73430")
    later = NOW + timedelta(seconds=3)

    assert await FailStuckSearches(s.jobs, s.settings, now=lambda: later)() == 1
    stuck = await s.jobs.get(job.id)
    assert stuck is not None
    assert (stuck.status, stuck.error_code) == (AiSearchStatus.FAILED, AiSearchError.TIMEOUT)


async def test_old_logs_are_compacted(s: Setup) -> None:
    job = await s.start(MODERATOR, "73430")
    await s.run(job.id)

    compact = CompactAiSearchLogs(s.jobs, now=lambda: NOW + timedelta(days=91))
    assert await compact() == 1
    stored = await s.jobs.get(job.id)
    assert stored is not None
    assert stored.log == {}
