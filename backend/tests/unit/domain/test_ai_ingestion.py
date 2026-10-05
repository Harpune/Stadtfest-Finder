from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from stadtfest.domain.ai_ingestion.categories import map_category
from stadtfest.domain.ai_ingestion.finds import FoundEvent, domain_of, normalize_url
from stadtfest.domain.ai_ingestion.job import (
    AiSearchError,
    AiSearchJob,
    AiSearchStatus,
    InvalidJobTransitionError,
    SkipCounts,
    SkipReason,
)
from stadtfest.domain.ai_ingestion.prompt import SearchParameters, build_prompt

TODAY = date(2026, 10, 2)
NOW = datetime(2026, 10, 2, 9, tzinfo=UTC)


def _job() -> AiSearchJob:
    return AiSearchJob(uuid4(), uuid4(), "73430", "Aalen", NOW)


def test_job_runs_through_its_states() -> None:
    job = _job()
    job.start(NOW)
    job.complete((uuid4(),), SkipCounts().add(SkipReason.DUPLICATE), {"queries": 2}, NOW)

    assert job.status is AiSearchStatus.COMPLETED
    assert job.skipped.duplicate == 1
    with pytest.raises(InvalidJobTransitionError):
        job.start(NOW)


def test_job_cannot_start_twice_and_fails_with_a_code() -> None:
    job = _job()
    job.start(NOW)
    with pytest.raises(InvalidJobTransitionError):
        job.start(NOW)
    job.fail(AiSearchError.TIMEOUT, {}, NOW)
    assert (job.status, job.error_code) == (AiSearchStatus.FAILED, AiSearchError.TIMEOUT)
    with pytest.raises(InvalidJobTransitionError):
        job.fail(AiSearchError.INTERNAL, {}, NOW)


def _find(**changes: object) -> FoundEvent:
    values: dict[str, object] = {
        "name": "Aalener Weihnachtsmarkt",
        "date_from": date(2026, 11, 26),
        "date_to": date(2026, 12, 23),
        "place": "Marktplatz",
        "address": "Marktplatz 1, 73430 Aalen",
        "source_url": "https://www.aalen.de/weihnachtsmarkt",
    }
    return FoundEvent(**(values | changes))  # type: ignore[arg-type]


def test_finds_in_the_past_or_with_reversed_dates_are_invalid() -> None:
    assert _find().problems(TODAY) == []
    assert "past" in _find(date_from=date(2026, 9, 1), date_to=date(2026, 9, 2)).problems(TODAY)
    assert "dates_reversed" in _find(date_to=date(2026, 11, 1)).problems(TODAY)
    assert "source_url" in _find(source_url="ftp://x.de/a").problems(TODAY)


def test_coordinates_outside_germany_are_implausible() -> None:
    assert _find(lat=48.8, lon=10.1).plausible_location
    assert not _find(lat=0.0, lon=0.0).plausible_location
    assert not _find().plausible_location


@pytest.mark.parametrize(
    ("url", "normalized"),
    [
        ("https://www.Aalen.de/fest/", "https://aalen.de/fest"),
        ("http://aalen.de/fest?utm_source=x&b=2&a=1#top", "https://aalen.de/fest?a=1&b=2"),
    ],
)
def test_urls_are_normalized(url: str, normalized: str) -> None:
    assert normalize_url(url) == normalized


def test_domain_of() -> None:
    assert domain_of("https://www.schwaebisch-gmuend.de/x") == "schwaebisch-gmuend.de"


def test_prompt_contains_only_public_parameters() -> None:
    prompt = build_prompt(
        SearchParameters(
            "73430", "Aalen", 25, date(2026, 10, 2), date(2027, 10, 2), ("Stadtfest", "Kirmes")
        )
    )

    assert prompt == (
        "Finde Veranstaltungen im Umkreis von 25 km um 73430 Aalen, die zwischen "
        "2026-10-02 und 2027-10-02 stattfinden. Kategorien: Stadtfest, Kirmes. "
        "Gib für jede Veranstaltung Name, Beginn, Ende, Ort, Adresse, falls bekannt "
        "Koordinaten, die passende Kategorie, eine kurze Beschreibung und die Quelle an."
    )


ACTIVE = {
    "Stadtfest": uuid4(),
    "Volksfest & Kirmes": uuid4(),
    "Weihnachtsmarkt": uuid4(),
    "Markt & Messe": uuid4(),
}


@pytest.mark.parametrize(
    ("named", "expected"),
    [
        ("Stadtfest", "Stadtfest"),
        ("weihnachtsmarkt", "Weihnachtsmarkt"),
        ("Kirmes", "Volksfest & Kirmes"),
        ("Flohmarkt", "Markt & Messe"),
        ("Konzert", None),
        (None, None),
    ],
)
def test_categories_map_by_name_or_synonym(named: str | None, expected: str | None) -> None:
    result = map_category(named, ACTIVE)
    assert result == (ACTIVE[expected] if expected else None)
