from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from stadtfest.application.ai_ingestion.ports import SearchHit
from stadtfest.application.ai_ingestion.prompts import load_bundled
from stadtfest.application.ai_ingestion.use_cases import (
    PAGE_MAX_CHARS,
    READ_BUDGET_EXHAUSTED,
    READ_FAILED,
    READ_NOT_A_RESULT,
    READ_UNAVAILABLE,
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
    FakePageReader,
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
    def __init__(self, daily_limit: int = 3, prompt: str = "v2", page_reads: int = 6) -> None:
        self.jobs = FakeAiSearchRepository()
        accounts = FakeAccountResolver()
        self.geocoding = FakeGeocoding(places=[AALEN, WASSERALFINGEN, ULM], reverse_result=AALEN)
        self.search = FakeWebSearch(hits=[SearchHit(SOURCE, "Stadtfest Aalen")])
        self.finder = FakeEventFinder(finds=[_find()])
        self.sources = FakeSourceChecker()
        self.pages = FakePageReader({SOURCE: "Aalener Stadtfest, 17. bis 18. Oktober, Marktplatz"})
        self.drafts = FakeDraftStore()
        self.settings = AiSearchSettings(
            daily_limit=daily_limit,
            timeout_seconds=1,
            prompt=load_bundled(prompt),
            max_page_reads=page_reads,
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
            self.pages,
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
    assert "Du hast höchstens 8 Suchen." in system
    assert done is not None
    assert done.log["prompt"] == "v2"
    assert done.log["nearbyPlaces"] == ["Aalen"]
    assert len(s.geocoding.reverse_calls) == 17 + 1  # center + 6 + 10 points, + the find


async def test_other_towns_are_added_and_geocoding_failures_ignored(s: Setup) -> None:
    s.geocoding.reverse_result = ULM
    job = await s.start(MODERATOR, "73430")
    await s.run(job.id)
    assert "Orte im Umkreis: Aalen, Ulm." in s.finder.prompts[0][1]


async def test_one_failed_search_does_not_end_the_run(s: Setup) -> None:
    """Seen with SearXNG: parallel queries made single engines block."""
    s.finder.queries = ["Feste 73430", "Veranstaltungskalender Aalen"]
    s.search.failing = {"Veranstaltungskalender Aalen"}
    job = await s.start(MODERATOR, "73430")

    done = await s.run(job.id)

    assert done is not None
    assert done.status is AiSearchStatus.COMPLETED
    assert len(done.new_event_ids) == 1
    assert done.log["failedSearches"] == 1


async def test_all_searches_failed_means_search_unavailable(s: Setup) -> None:
    s.search.failing = {"Feste 73430"}
    job = await s.start(MODERATOR, "73430")
    done = await s.run(job.id)
    assert done is not None
    assert done.error_code is AiSearchError.SEARCH_UNAVAILABLE


async def test_only_result_pages_can_be_read_and_are_logged(s: Setup) -> None:
    """R10b-US5: no invented or internal URLs; the page text goes to the model."""
    s.finder.reads = [SOURCE, "http://10.0.0.1/admin", "https://www.aalen.de/stadtfest/"]
    s.pages.texts["https://www.aalen.de/stadtfest/"] = "Aalener Stadtfest (gleiche Seite)"
    job = await s.start(MODERATOR, "73430")

    done = await s.run(job.id)

    page, invented, same_page = s.finder.read_results
    assert page.startswith("Aalener Stadtfest")
    assert invented == READ_NOT_A_RESULT
    assert same_page.startswith("Aalener Stadtfest")  # same page, normalized URL
    assert s.pages.calls == [
        (SOURCE, PAGE_MAX_CHARS),
        ("https://www.aalen.de/stadtfest/", PAGE_MAX_CHARS),
    ]
    assert done is not None
    assert done.log["pages"] == [SOURCE, "https://www.aalen.de/stadtfest/"]


async def test_page_budget_and_unreadable_pages() -> None:
    s = Setup(page_reads=1)
    s.pages.texts = {}
    s.finder.reads = [SOURCE, SOURCE]
    job = await s.start(MODERATOR, "73430")
    await s.run(job.id)
    assert s.finder.read_results == [READ_FAILED, READ_BUDGET_EXHAUSTED]


async def test_reading_is_off_with_zero_budget() -> None:
    s = Setup(page_reads=0)
    s.finder.reads = [SOURCE]
    job = await s.start(MODERATOR, "73430")
    await s.run(job.id)
    assert s.finder.read_results == [READ_UNAVAILABLE]
    assert s.pages.calls == []


async def test_vague_addresses_fall_back_to_postal_code_and_town(s: Setup) -> None:
    """Seen in make ai-eval: "Innenstadt, 73441 Bopfingen" was not found."""
    s.geocoding.by_query = {"73430": [AALEN], "73433 Aalen": [WASSERALFINGEN]}
    s.geocoding.reverse_result = WASSERALFINGEN
    s.finder.finds = [_find(lat=None, lon=None, address="Innenstadt, 73433 Aalen")]
    job = await s.start(MODERATOR, "73430")

    done = await s.run(job.id)

    assert done is not None
    assert len(done.new_event_ids) == 1
    assert s.drafts.stored[0].location == WASSERALFINGEN.location
    assert s.geocoding.search_calls[-3:] == [
        "Innenstadt, 73433 Aalen",
        "Marktplatz, 73433 Aalen",
        "73433 Aalen",
    ]


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
