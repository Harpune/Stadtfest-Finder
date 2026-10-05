"""`make ai-eval`: runs the pipeline in memory and reports per prompt version."""

from __future__ import annotations

from typing import cast

from stadtfest.adapters.outbound.clock.berlin_clock import BerlinClock
from stadtfest.adapters.outbound.persistence.ai_search import SqlDraftStore
from stadtfest.adapters.outbound.persistence.catalog import SqlCatalog
from stadtfest.application.ai_ingestion.ports import SearchHit
from stadtfest.application.ai_ingestion.prompts import load_bundled
from stadtfest.application.ai_ingestion.use_cases import AiSearchSettings
from stadtfest.bootstrap import ai_eval
from stadtfest.bootstrap.container import AiSearchParts
from tests.fakes import (
    FakeDraftStore,
    FakeEventFinder,
    FakeGeocoding,
    FakeSourceChecker,
    FakeWebSearch,
    FixedClock,
)
from tests.unit.application.test_ai_search_use_cases import (
    AALEN,
    SOURCE,
    TODAY,
    _Catalog,
    _find,
)


def _parts() -> AiSearchParts:
    return AiSearchParts(
        finder=FakeEventFinder(finds=[_find()]),
        search=FakeWebSearch(hits=[SearchHit(SOURCE, "Stadtfest Aalen")]),
        sources=FakeSourceChecker(),
        geocoding=FakeGeocoding(places=[AALEN], reverse_result=AALEN),
        catalog=cast("SqlCatalog", _Catalog()),
        clock=cast("BerlinClock", FixedClock(TODAY)),
        settings=AiSearchSettings(timeout_seconds=5),
    )


async def test_eval_collects_drafts_without_storing_and_reports_both_prompts() -> None:
    store = FakeDraftStore()
    sql = cast("SqlDraftStore", store)
    runs = [
        await ai_eval._run_one(_parts(), sql, "73430", load_bundled(version))
        for version in ("v1", "v2")
    ]
    unknown = await ai_eval._run_one(_parts(), sql, "99999", load_bundled("v2"))

    assert [len(run.drafts) for run in runs] == [1, 1]
    assert store.stored == []  # nothing reached the draft store
    report = ai_eval._report([*runs, unknown])
    assert "| 73430 | v1 | completed | 1 |" in report
    assert "| 73430 | v2 | completed | 1 |" in report
    assert "| 99999 | v2 | postal code unknown |" in report
    assert "- Aalener Stadtfest · 17.10.2026-18.10.2026 · Aalen · " + SOURCE in report
