"""MCP tools (R15-US3): parse the input, call the use case, map the result.

No business logic here: visibility, roles and limits live in the use cases shared with REST.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from stadtfest.adapters.inbound.mcp.auth import current_principal
from stadtfest.adapters.inbound.mcp.dependencies import McpConfig, McpDependencies
from stadtfest.adapters.inbound.mcp.errors import tool_errors
from stadtfest.application.events.criteria import MAX_RADIUS_KM, MIN_RADIUS_KM, SearchFilter
from stadtfest.application.events.views import EventDetailView, EventSummaryView
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.time_filter import TimeFilter

SEARCH_LIMIT = 50
DEFAULT_RADIUS_KM = 25
LOGIN_TOOLS = frozenset({"start_ai_search"})

SEARCH_DESCRIPTION = """\
Sucht veröffentlichte Feste (Stadtfeste, Volksfeste, Kirmes, Weihnachtsmärkte, Märkte) in \
Deutschland im Umkreis einer Postleitzahl. Ohne Zeitraum: laufende und kommende Feste. \
Höchstens 50 Treffer, sortiert nach Beginn.
Searches published festivals and fairs in Germany around a German postal code (5 digits). \
Without dates: running and upcoming events. At most 50 results, ordered by start date. \
Only published events, only Germany."""

GET_DESCRIPTION = """\
Liefert die Details eines veröffentlichten Fests (Programm, Öffnungszeiten, Anfahrt, Link).
Returns the details of a published event in Germany by its ID (from `search_events`)."""

START_DESCRIPTION = """\
Startet die KI-Suche nach neuen Festen um eine Postleitzahl. Nur für Moderatoren mit \
Anmeldung. Funde werden als Entwürfe gespeichert und erst nach Prüfung veröffentlicht.
Starts the AI search for new events around a German postal code. Moderators only (sign-in \
required). Finds are stored as drafts and published only after a moderator reviews them."""

ZipCode = Annotated[
    str, Field(pattern=r"^\d{5}$", description="Deutsche Postleitzahl / German postal code")
]


class _Model(BaseModel):
    """Output models: camelCase like the REST API."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True, frozen=True
    )


class EventItem(_Model):
    """One search result."""

    id: str
    name: str
    start_date: date
    end_date: date
    place: str
    city: str
    category: str
    distance_km: float | None
    status: Literal["published", "cancelled"]
    url: str = Field(description="Link, der das Fest in der App öffnet / opens the event")


class EventSearchResult(_Model):
    """Search results; `more_available` if the 50 results were cut off."""

    events: list[EventItem]
    more_available: bool


class ProgramItem(_Model):
    """Program entry of an event."""

    date: date
    time_label: str
    title: str
    subtitle: str | None


class EventDetail(_Model):
    """Public event detail (without user-specific fields)."""

    id: str
    name: str
    short_name: str
    status: Literal["published", "cancelled"]
    cancel_reason: str | None
    category: str
    start_date: date
    end_date: date
    opening_hours: list[str]
    price: str | None
    place: str
    address: str
    city: str
    postal_code: str
    lat: float
    lon: float
    description: str | None
    program: list[ProgramItem]
    transit: str | None
    parking: str | None
    website_url: str | None
    image_urls: list[str]
    url: str


class AiSearchStarted(_Model):
    """The queued AI search job."""

    job_id: str
    status: str


def _status(status: EventStatus) -> Literal["published", "cancelled"]:
    # Only published and cancelled events are public (enforced by the catalog query).
    return "cancelled" if status is EventStatus.CANCELLED else "published"


def _item(event: EventSummaryView, category: str, config: McpConfig) -> EventItem:
    return EventItem(
        id=str(event.id),
        name=event.name,
        start_date=event.start_date,
        end_date=event.end_date,
        place=event.place,
        city=event.city,
        category=category,
        distance_km=event.distance_km,
        status=_status(event.status),
        url=config.event_url(str(event.id)),
    )


def _detail(event: EventDetailView, config: McpConfig) -> EventDetail:
    return EventDetail(
        id=str(event.id),
        name=event.name,
        short_name=event.short_name,
        status=_status(event.status),
        cancel_reason=event.cancel_reason,
        category=event.category.name,
        start_date=event.start_date,
        end_date=event.end_date,
        opening_hours=list(event.opening_hours),
        price=event.price,
        place=event.place,
        address=event.address,
        city=event.city,
        postal_code=event.postal_code,
        lat=event.location.lat,
        lon=event.location.lon,
        description=event.description,
        program=[
            ProgramItem(
                date=item.date, time_label=item.time_label, title=item.title, subtitle=item.subtitle
            )
            for item in event.program
        ],
        transit=event.transit,
        parking=event.parking,
        website_url=event.website_url,
        image_urls=[image.url for image in event.images],
        url=config.event_url(str(event.id)),
    )


def _time_filter(date_from: date | None, date_to: date | None) -> TimeFilter:
    """Overlap with `date_from`-`date_to`; an open end is unlimited."""
    if date_from is None and date_to is None:
        return TimeFilter()
    try:
        return TimeFilter.between(date_from or date.min, date_to or date.max)
    except ValueError:
        raise ToolError(
            "date_to liegt vor date_from. / date_to must not be before date_from."
        ) from None


def register_tools(server: FastMCP, deps: McpDependencies, config: McpConfig) -> None:
    """Register the three tools of R15 on the server.

    Args:
        server: The FastMCP server.
        deps: Use cases from the composition root.
        config: Public addresses (deep links).
    """

    @server.tool(
        name="search_events",
        description=SEARCH_DESCRIPTION,
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
    )
    async def search_events(
        zip_code: ZipCode,
        radius_km: Annotated[
            int,
            Field(ge=MIN_RADIUS_KM, le=MAX_RADIUS_KM, description="Umkreis / radius in km"),
        ] = DEFAULT_RADIUS_KM,
        date_from: Annotated[
            date | None, Field(description="Frühestes Datum / from (ISO date)")
        ] = None,
        date_to: Annotated[
            date | None, Field(description="Spätestes Datum / to (ISO date)")
        ] = None,
    ) -> EventSearchResult:
        time_filter = _time_filter(date_from, date_to)
        with tool_errors():
            place = await deps.locate_postal_code(zip_code)
            search = SearchFilter(reference=place.location, radius_km=radius_km, time=time_filter)
            page = await deps.search_events(search, None, SEARCH_LIMIT)
            categories = await deps.list_active_categories()
        names = {category.id: category.name for category in categories.categories}
        return EventSearchResult(
            events=[_item(event, names.get(event.category_id, ""), config) for event in page.items],
            more_available=page.next_cursor is not None,
        )

    @server.tool(
        name="get_event",
        description=GET_DESCRIPTION,
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
    )
    async def get_event(
        event_id: Annotated[UUID, Field(description="ID aus / from search_events")],
    ) -> EventDetail:
        with tool_errors():
            event = await deps.get_public_event(event_id)
        return _detail(event, config)

    @server.tool(
        name="start_ai_search",
        description=START_DESCRIPTION,
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def start_ai_search(zip_code: ZipCode) -> AiSearchStarted:
        principal = current_principal()
        if principal is None:  # normally answered with HTTP 401 by `OptionalBearerAuth`
            raise ToolError("Anmeldung erforderlich. / Sign-in required (OAuth).")
        with tool_errors():
            job = await deps.start_ai_search(principal, zip_code)
        return AiSearchStarted(job_id=str(job.id), status=job.status.value)
