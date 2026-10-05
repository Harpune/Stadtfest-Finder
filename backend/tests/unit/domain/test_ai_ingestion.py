from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from stadtfest.application.ai_ingestion.prompts import bundled_versions, load_bundled
from stadtfest.domain.ai_ingestion.categories import map_category
from stadtfest.domain.ai_ingestion.finds import (
    FoundEvent,
    domain_of,
    geocoding_queries,
    normalize_name,
    normalize_url,
)
from stadtfest.domain.ai_ingestion.job import (
    AiSearchError,
    AiSearchJob,
    AiSearchStatus,
    InvalidJobTransitionError,
    SkipCounts,
    SkipReason,
)
from stadtfest.domain.ai_ingestion.prompt import (
    InvalidPromptError,
    PromptTemplate,
    SearchParameters,
    parse_prompt,
)

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


PARAMETERS = SearchParameters(
    "73430",
    "Aalen",
    25,
    date(2026, 10, 2),
    date(2027, 10, 2),
    ("Stadtfest", "Kirmes"),
    ("Aalen", "Oberkochen", "Ellwangen (Jagst)"),
)


def test_prompt_v1_is_unchanged() -> None:
    """v1 stays byte-identical to the R10 prompt, so search results remain comparable."""
    prompt = load_bundled("v1").render(PARAMETERS).user

    assert prompt == (
        "Finde Veranstaltungen im Umkreis von 25 km um 73430 Aalen, die zwischen "
        "2026-10-02 und 2027-10-02 stattfinden. Kategorien: Stadtfest, Kirmes. "
        "Gib für jede Veranstaltung Name, Beginn, Ende, Ort, Adresse, falls bekannt "
        "Koordinaten, die passende Kategorie, eine kurze Beschreibung und die Quelle an."
    )


def test_prompt_v2_names_the_towns_and_years_but_no_iso_dates_in_rules() -> None:
    prompt = load_bundled("v2").render(PARAMETERS)

    assert "Orte im Umkreis: Aalen, Oberkochen, Ellwangen (Jagst)." in prompt.user
    assert "Zeitraum: 2026-10-02 bis 2027-10-02." in prompt.user
    assert "„Stadtfest Ellwangen 2026/2027“" in prompt.system
    assert "{" not in prompt.system + prompt.user


def test_bundled_versions_are_valid() -> None:
    assert {"v1", "v2", "v3"} <= set(bundled_versions())
    for version in bundled_versions():
        assert load_bundled(version).version == version
    with pytest.raises(InvalidPromptError):
        load_bundled("v99")


@pytest.mark.parametrize(
    "user",
    [
        "Suche für {moderator_name}",  # not in the allowlist: could carry personal data
        "Suche für {postal_code.__class__}",
        "Suche für {",
        "  ",
    ],
)
def test_templates_reject_unknown_placeholders(user: str) -> None:
    with pytest.raises(InvalidPromptError):
        PromptTemplate("test", "System", user)


def test_prompt_files_need_both_markers() -> None:
    text = "Kommentar\n<!-- system -->\nS {years}\n<!-- user -->\nU {postal_code}\n"
    template = parse_prompt("x", text)
    assert (template.system, template.user) == ("S {years}", "U {postal_code}")
    with pytest.raises(InvalidPromptError):
        parse_prompt("x", "<!-- user -->\nU")


def test_without_nearby_places_the_place_itself_is_named() -> None:
    values = SearchParameters(
        "73430", "Aalen", 25, date(2026, 1, 2), date(2026, 12, 2), ()
    ).values()
    assert (values["nearby_places"], values["years"], values["categories"]) == (
        "Aalen",
        "2026",
        "alle",
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


def _vague(address: str, place: str) -> FoundEvent:
    return FoundEvent(
        name="Bopfinger Heimattage",
        date_from=date(2026, 10, 9),
        date_to=date(2026, 10, 11),
        place=place,
        address=address,
        source_url="https://www.bopfingen.de/stadtfeste.html",
    )


def test_geocoding_queries_go_from_exact_to_coarse() -> None:
    """Seen in make ai-eval: "Innenstadt, 73441 Bopfingen" was not found and counted as outside."""
    queries = geocoding_queries(_vague("Innenstadt, 73441 Bopfingen", "Innenstadt Bopfingen"))
    assert queries == [
        "Innenstadt, 73441 Bopfingen",
        "Innenstadt Bopfingen, 73441 Bopfingen",
        "73441 Bopfingen",
        "73441",
    ]
    assert geocoding_queries(_vague("", "Marktplatz Aalen")) == ["Marktplatz Aalen"]


def test_names_are_normalized_for_comparisons() -> None:
    assert normalize_name("  Ipfmess  Bopfingen! ") == normalize_name("ipfmess bopfingen")
    assert normalize_name('Bopfinger Kneipentour "City Sounds"') == (
        "bopfinger kneipentour city sounds"
    )
