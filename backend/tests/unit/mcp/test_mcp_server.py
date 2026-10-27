"""MCP server tests over the real HTTP stack (in-process) with fakes (R15).

Covers the role checks of all tools (CLAUDE.md "Testing"): guests may search and read,
`start_ai_search` needs a token (401 challenge) and the role `moderator` (tool error).
"""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any, get_type_hints
from uuid import UUID, uuid4

import pytest
from fastmcp.exceptions import ToolError
from fastmcp.utilities.tests import ASGIServer, asgi_server

from stadtfest.adapters.inbound.mcp import server as mcp_server
from stadtfest.adapters.inbound.mcp.dependencies import McpConfig, McpDependencies
from stadtfest.adapters.inbound.mcp.server import create_mcp_server, http_app_options
from stadtfest.adapters.inbound.rest.dependencies import RestDependencies
from stadtfest.application.ai_ingestion.use_cases import AiSearchSettings, StartAiSearch
from stadtfest.application.events.use_cases import (
    GetPublicEvent,
    ListActiveCategories,
    SearchEvents,
)
from stadtfest.application.events.views import (
    CategoryView,
    EventDetailView,
    EventSummaryView,
    ProgramItemView,
)
from stadtfest.application.geocoding.ports import Place, PlaceKind
from stadtfest.application.geocoding.use_cases import Geocode, LocatePostalCode
from stadtfest.application.health.check_readiness import CheckReadiness
from stadtfest.application.identity.claims import ClaimMapping
from stadtfest.application.identity.use_cases import Authenticate
from stadtfest.bootstrap.logging import configure_logging
from stadtfest.bootstrap.settings import GeocodingProvider, LogFormat, Settings
from stadtfest.domain.ai_ingestion.job import AiSearchFilters, SearchFocus
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.events.time_filter import DateRange
from tests.fakes import (
    FakeAccountResolver,
    FakeAiSearchRepository,
    FakeCache,
    FakeCategoryCatalog,
    FakeDeletedAccounts,
    FakeEventCatalog,
    FakeGeocoding,
    FakeRateLimiter,
    FakeTokenVerifier,
    FixedClock,
)
from tests.settings_values import TEST_STORAGE

TODAY = date(2026, 10, 15)
AALEN = Place("73430 Aalen", "Aalen", GeoPoint(48.8375, 10.0933), PlaceKind.POSTCODE, "73430")
CATEGORY = CategoryView(UUID("00000000-0000-0000-0000-00000000000a"), "Stadtfest", "🎪", "#F", 0)
EVENT_ID = UUID("24b84e9c-31ad-4b5e-9a39-3f4d2c0f6a11")
CONFIG = McpConfig(
    public_url="https://mcp.example.test",
    authorization_server="https://idp.example.test",
    link_base_url="https://links.example.test",
)
MOD = {"Authorization": "Bearer mod"}
USER = {"Authorization": "Bearer user"}
ACCEPT = {"Accept": "application/json, text/event-stream"}


def _summary() -> EventSummaryView:
    return EventSummaryView(
        id=EVENT_ID,
        name="Reichsstädter Tage",
        short_name="Reichsstädter",
        status=EventStatus.PUBLISHED,
        start_date=TODAY,
        end_date=TODAY + timedelta(days=2),
        place="Marktplatz",
        city="Aalen",
        location=GeoPoint(48.8368, 10.0932),
        category_id=CATEGORY.id,
        distance_km=1.4,
    )


def _detail() -> EventDetailView:
    return EventDetailView(
        id=EVENT_ID,
        name="Reichsstädter Tage",
        short_name="Reichsstädter",
        status=EventStatus.CANCELLED,
        cancel_reason="Unwetter",
        category=CATEGORY,
        start_date=TODAY,
        end_date=TODAY + timedelta(days=2),
        opening_hours=("Fr 18-24 Uhr",),
        price="Frei",
        place="Marktplatz",
        address="Marktplatz 1",
        city="Aalen",
        postal_code="73430",
        location=GeoPoint(48.8368, 10.0932),
        description="Stadtfest",
        program=(ProgramItemView(TODAY, "10:45 Uhr", "Umzug", None),),
        transit=None,
        parking=None,
        website_url="https://example.test/fest",
    )


@dataclass
class World:
    server: ASGIServer
    catalog: FakeEventCatalog
    jobs: FakeAiSearchRepository
    limiter: FakeRateLimiter
    deps: Any  # SimpleNamespace standing in for the container


def _deps(
    catalog: FakeEventCatalog, jobs: FakeAiSearchRepository, limiter: FakeRateLimiter
) -> SimpleNamespace:
    cache = FakeCache()
    clock = FixedClock(TODAY)
    geocoding = FakeGeocoding(places=[AALEN])
    verifier = FakeTokenVerifier(
        {
            "mod": {"sub": "m", "realm_access": {"roles": ["moderator"]}},
            "user": {"sub": "u", "realm_access": {"roles": ["user"]}},
        }
    )
    return SimpleNamespace(
        check_readiness=CheckReadiness([]),
        authenticate=Authenticate(
            verifier, ClaimMapping("realm_access.roles"), FakeDeletedAccounts()
        ),
        locate_postal_code=LocatePostalCode(Geocode(geocoding, cache)),
        search_events=SearchEvents(catalog, cache, clock),
        get_public_event=GetPublicEvent(catalog),
        list_active_categories=ListActiveCategories(FakeCategoryCatalog([CATEGORY]), cache),
        start_ai_search=StartAiSearch(
            jobs,
            FakeAccountResolver(),
            geocoding,
            FakeCategoryCatalog([CATEGORY]),
            clock,
            AiSearchSettings(daily_limit=5),
            now=lambda: datetime(2026, 10, 15, 9, tzinfo=UTC),
        ),
        rate_limiter=limiter,
    )


@pytest.fixture
async def world() -> AsyncIterator[World]:
    catalog = FakeEventCatalog(rows=[_summary()], details={EVENT_ID: _detail()})
    jobs = FakeAiSearchRepository()
    limiter = FakeRateLimiter()
    deps = _deps(catalog, jobs, limiter)
    server = create_mcp_server(deps, CONFIG)
    async with asgi_server(server, **http_app_options(deps, CONFIG)) as running:
        yield World(running, catalog, jobs, limiter, deps)


def _call(tool: str, arguments: dict[str, object]) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }


# --- public tools ------------------------------------------------------------------------


async def test_guests_list_all_tools(world: World) -> None:
    async with world.server.client() as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    assert set(tools) == {"search_events", "get_event", "start_ai_search"}
    assert "Deutschland" in (tools["search_events"].description or "")
    assert "Germany" in (tools["search_events"].description or "")
    assert tools["search_events"].annotations is not None
    assert tools["search_events"].annotations.read_only_hint is True


async def test_guests_search_events_around_a_postal_code(world: World) -> None:
    async with world.server.client() as client:
        result = await client.call_tool(
            "search_events",
            {"zip_code": "73430", "radius_km": 50, "date_from": "2026-10-16"},
        )

    assert result.structured_content == {
        "events": [
            {
                "id": str(EVENT_ID),
                "name": "Reichsstädter Tage",
                "startDate": "2026-10-15",
                "endDate": "2026-10-17",
                "place": "Marktplatz",
                "city": "Aalen",
                "category": "Stadtfest",
                "distanceKm": 1.4,
                "status": "published",
                "url": f"https://links.example.test/f/{EVENT_ID}",
            }
        ],
        "moreAvailable": False,
    }
    criteria, cursor, limit = world.catalog.search_calls[0]
    assert criteria.filter.reference == AALEN.location
    assert criteria.filter.radius_km == 50
    assert criteria.windows == (DateRange(date(2026, 10, 16), date.max),)
    assert (cursor, limit) == (None, 51)  # 50 results, one more to detect a cut-off


async def test_postal_codes_sent_as_numbers_are_accepted(world: World) -> None:
    # The MCP Inspector CLI (and some LLM clients) send digits as JSON numbers.
    async with world.server.client(headers=MOD) as client:
        await client.call_tool("search_events", {"zip_code": 73430})
        started = await client.call_tool("start_ai_search", {"zip_code": 73430})
        with pytest.raises(ToolError, match="Postleitzahl"):
            await client.call_tool("search_events", {"zip_code": 1067})  # -> "01067"

    assert world.catalog.search_calls[0][0].filter.reference == AALEN.location
    assert started.structured_content is not None


async def test_search_defaults_to_25_km_and_all_dates(world: World) -> None:
    async with world.server.client() as client:
        await client.call_tool("search_events", {"zip_code": "73430"})

    criteria = world.catalog.search_calls[0][0]
    assert criteria.filter.radius_km == 25
    assert criteria.windows is None


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"zip_code": "99999"}, "Postleitzahl"),
        ({"zip_code": "7343"}, "zip_code"),
        ({"zip_code": "73430", "radius_km": 5}, "radius_km"),
        ({"zip_code": "73430", "date_from": "2026-10-20", "date_to": "2026-10-19"}, "date_to"),
    ],
)
async def test_search_rejects_invalid_input(
    world: World, arguments: dict[str, object], message: str
) -> None:
    async with world.server.client() as client:
        with pytest.raises(ToolError, match=message):
            await client.call_tool("search_events", arguments)


async def test_guests_get_an_event_without_user_fields(world: World) -> None:
    async with world.server.client() as client:
        result = await client.call_tool("get_event", {"event_id": str(EVENT_ID)})

    detail = result.structured_content
    assert detail is not None
    assert detail["status"] == "cancelled"
    assert detail["cancelReason"] == "Unwetter"
    assert detail["category"] == "Stadtfest"
    assert detail["program"] == [
        {"date": "2026-10-15", "timeLabel": "10:45 Uhr", "title": "Umzug", "subtitle": None}
    ]
    assert detail["url"] == f"https://links.example.test/f/{EVENT_ID}"
    assert "isFavorite" not in detail
    assert "invitationSummary" not in detail


async def test_unknown_event_is_a_readable_tool_error(world: World) -> None:
    async with world.server.client() as client:
        with pytest.raises(ToolError, match="nicht veröffentlicht"):
            await client.call_tool("get_event", {"event_id": str(uuid4())})


async def test_users_may_use_the_public_tools(world: World) -> None:
    async with world.server.client(headers=USER) as client:
        result = await client.call_tool("get_event", {"event_id": str(EVENT_ID)})
    assert result.structured_content is not None


# --- authentication and roles -----------------------------------------------------------


async def test_start_ai_search_without_token_is_challenged(world: World) -> None:
    async with world.server.http_client(headers=ACCEPT) as http:
        response = await http.post("/mcp", json=_call("start_ai_search", {"zip_code": "73430"}))

    assert response.status_code == 401
    challenge = response.headers["www-authenticate"]
    assert challenge.startswith("Bearer ")
    assert (
        'resource_metadata="https://mcp.example.test/.well-known/oauth-protected-resource/mcp"'
        in challenge
    )
    assert "error=" not in challenge  # missing, not invalid credentials (RFC 6750 §3.1)
    assert "Anmeldung" in response.json()["message"]
    assert world.jobs.jobs == {}


async def test_public_tool_calls_pass_without_token(world: World) -> None:
    async with world.server.http_client(headers=ACCEPT) as http:
        response = await http.post("/mcp", json=_call("get_event", {"event_id": str(EVENT_ID)}))
    assert response.status_code == 200


async def test_invalid_token_is_rejected_on_every_tool(world: World) -> None:
    headers = ACCEPT | {"Authorization": "Bearer expired"}
    async with world.server.http_client(headers=headers) as http:
        response = await http.post("/mcp", json=_call("get_event", {"event_id": str(EVENT_ID)}))

    assert response.status_code == 401
    assert 'error="invalid_token"' in response.headers["www-authenticate"]


async def test_start_ai_search_as_user_is_forbidden(world: World) -> None:
    async with world.server.client(headers=USER) as client:
        with pytest.raises(ToolError, match="Moderator"):
            await client.call_tool("start_ai_search", {"zip_code": "73430"})
    assert world.jobs.jobs == {}


async def test_moderators_start_an_ai_search(world: World) -> None:
    async with world.server.client(headers=MOD) as client:
        result = await client.call_tool("start_ai_search", {"zip_code": "73430"})

    assert result.structured_content is not None
    assert result.structured_content["status"] == "queued"
    job = world.jobs.jobs[UUID(str(result.structured_content["jobId"]))]
    assert (job.postal_code, job.place_name) == ("73430", "Aalen")


async def test_moderators_start_an_ai_search_with_filters(world: World) -> None:
    """R10c: optional filters; categories by name, focuses from a fixed list."""
    arguments = {
        "zip_code": "73430",
        "date_from": "2026-11-20",
        "date_to": "2026-12-24",
        "categories": ["stadtfest"],
        "radius_km": 10,
        "focus": ["municipal_calendars"],
    }
    async with world.server.client(headers=MOD) as client:
        result = await client.call_tool("start_ai_search", arguments)

    assert result.structured_content is not None
    job = world.jobs.jobs[UUID(str(result.structured_content["jobId"]))]
    assert job.filters == AiSearchFilters(
        date_from=date(2026, 11, 20),
        date_to=date(2026, 12, 24),
        category_ids=(CATEGORY.id,),
        radius_km=10,
        focus=(SearchFocus.MUNICIPAL_CALENDARS,),
    )


@pytest.mark.parametrize(
    ("arguments", "match"),
    [
        ({"categories": ["Kirmes"]}, "Kategorie"),
        ({"focus": ["frei formuliert"]}, "focus"),
        ({"radius_km": 80}, "radius_km"),
        ({"date_from": "2026-01-01"}, "Ungültige Eingabe"),
        ({"prompt": "Suche bei Familie Müller"}, "prompt"),
    ],
)
async def test_ai_search_filters_are_checked(
    world: World, arguments: dict[str, object], match: str
) -> None:
    async with world.server.client(headers=MOD) as client:
        with pytest.raises(ToolError, match=match):
            await client.call_tool("start_ai_search", {"zip_code": "73430"} | arguments)
    assert world.jobs.jobs == {}


async def test_running_search_and_unknown_postal_code_are_tool_errors(world: World) -> None:
    async with world.server.client(headers=MOD) as client:
        first = await client.call_tool("start_ai_search", {"zip_code": "73430"})
        assert first.structured_content is not None
        with pytest.raises(ToolError, match=str(first.structured_content["jobId"])):
            await client.call_tool("start_ai_search", {"zip_code": "73430"})
        with pytest.raises(ToolError, match="Postleitzahl"):
            await client.call_tool("start_ai_search", {"zip_code": "99999"})


async def test_protected_resource_metadata_names_the_idp(world: World) -> None:
    async with world.server.http_client() as http:
        response = await http.get("/.well-known/oauth-protected-resource/mcp")

    assert response.status_code == 200
    assert response.json() == {
        "resource": "https://mcp.example.test/mcp",
        "authorization_servers": ["https://idp.example.test"],
        "scopes_supported": ["openid", "profile"],
        "bearer_methods_supported": ["header"],
        "resource_name": "Stadtfest-Finder",
    }


async def test_health(world: World) -> None:
    async with world.server.http_client() as http:
        live = await http.get("/health/live")
        ready = await http.get("/health/ready")
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 200


# --- rate limit, logging, shared use cases ------------------------------------------------


async def test_rate_limit_per_token_or_ip(world: World) -> None:
    async with world.server.client(headers=USER) as client:
        await client.call_tool("get_event", {"event_id": str(EVENT_ID)})
    async with world.server.client() as client:
        await client.call_tool("get_event", {"event_id": str(EVENT_ID)})

    keys = sorted(world.limiter.counts)
    assert keys[0].startswith("mcp:ip:")
    assert keys[1] == "mcp:sub:u"


async def test_rate_limited_calls_are_tool_errors(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mcp_server, "RATE_LIMIT_CALLS", 1)
    async with world.server.client() as client:
        await client.call_tool("get_event", {"event_id": str(EVENT_ID)})
        with pytest.raises(ToolError, match="60"):
            await client.call_tool("get_event", {"event_id": str(EVENT_ID)})


async def test_tool_calls_are_logged_without_inputs_or_user(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging(
        Settings(
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",
            redis_url="redis://localhost:6379/0",
            log_format=LogFormat.JSON,
            geocoding_provider=GeocodingProvider.FAKE,
            **TEST_STORAGE,  # type: ignore[arg-type]
        )
    )
    capsys.readouterr()

    async with world.server.client(headers=MOD) as client:
        await client.call_tool("start_ai_search", {"zip_code": "73430"})

    output = capsys.readouterr().out
    lines = [json.loads(line) for line in output.strip().splitlines()]
    calls = [line for line in lines if line["event"] == "mcp_tool_call"]
    assert len(calls) == 1
    assert {key: calls[0][key] for key in ("tool", "outcome")} == {
        "tool": "start_ai_search",
        "outcome": "ok",
    }
    assert set(calls[0]) <= {
        "event",
        "tool",
        "outcome",
        "duration_ms",
        "level",
        "timestamp",
        "logger",
        "request_id",
    }
    assert "73430" not in output
    assert "Bearer" not in output


def test_tools_use_the_same_use_cases_as_rest() -> None:
    """No duplication: the MCP adapter depends on the use case types the REST routers use."""
    mcp = get_type_hints(McpDependencies)
    rest = get_type_hints(RestDependencies)
    shared = {"authenticate", "search_events", "get_public_event", "start_ai_search"}
    shared |= {"list_active_categories", "check_readiness"}
    assert {name: mcp[name] for name in shared} == {name: rest[name] for name in shared}
    assert mcp["start_ai_search"] is StartAiSearch
    assert mcp["search_events"] is SearchEvents
    assert mcp["get_public_event"] is GetPublicEvent


async def test_input_schema_documents_the_postal_code_format(world: World) -> None:
    async with world.server.client() as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
    schema = tools["search_events"].input_schema["properties"]
    assert schema["zip_code"]["pattern"] == r"^\d{5}$"
    assert (schema["radius_km"]["minimum"], schema["radius_km"]["maximum"]) == (10, 300)
