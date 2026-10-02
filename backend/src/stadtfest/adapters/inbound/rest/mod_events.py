"""`/v1/mod/events`: event maintenance for moderators (R07).

Thin adapter: parse and translate; authorization and rules live in the use cases.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Query, Response

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.adapters.inbound.rest.errors import error_response
from stadtfest.application.moderation.use_cases import ModEventRow, ModEventView, ModStatus
from stadtfest.application.shared.errors import InvalidInputError
from stadtfest.domain.events.maintenance import EventContent, ProgramEntry
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/mod/events", tags=["moderation"])

# Content fields that are not nullable in the domain: `null` resets them to empty.
_EMPTY_VALUES: dict[str, object] = {
    "place": "",
    "address": "",
    "city": "",
    "short_name": "",
    "opening_hours": (),
    "program": (),
}


def _source(value: str) -> api.EventSource:
    return api.EventSource("ai" if value == "ai" else "manual")


def _etag(version: int) -> dict[str, str]:
    return {"ETag": f'"{version}"'}


def _program(items: list[api.ModProgramItem]) -> tuple[ProgramEntry, ...]:
    return tuple(
        ProgramEntry(item.date, item.time_label.strip(), item.title.strip(), item.subtitle)
        for item in items
    )


def _domain_value(name: str, value: Any) -> object:  # noqa: ANN401  # generated field types vary
    if value is None:
        return _EMPTY_VALUES.get(name)
    if name == "program":
        return _program(value)
    if name == "opening_hours":
        # Items are generated as RootModel wrappers (string with a length limit).
        lines = (str(getattr(line, "root", line)).strip() for line in value)
        return tuple(line for line in lines if line)
    if isinstance(value, str):
        return value.strip()
    return value


def _changes(body: api.ModEventFields) -> dict[str, object]:
    """Fields present in the request body, converted to domain values (merge patch)."""
    return {
        name: _domain_value(name, getattr(body, name))
        for name in body.model_fields_set
        if name != "name" or getattr(body, name) is not None
    }


def _detail(view: ModEventView) -> api.ModEventDetail:
    event, c = view.event, view.event.content
    return api.ModEventDetail(
        id=event.id,
        region_id=event.region_id,
        name=c.name,
        short_name=c.short_name,
        status=api.ModEventStatus(view.status.value),
        category_id=c.category_id,
        start_date=c.start_date,
        end_date=c.end_date,
        opening_hours=list(c.opening_hours),
        price=c.price,
        place=c.place,
        address=c.address,
        city=c.city,
        postal_code=c.postal_code,
        lat=c.lat,
        lon=c.lon,
        description=c.description,
        program=[
            api.ModProgramItem(
                date=entry.date,
                time_label=entry.time_label,
                title=entry.title,
                subtitle=entry.subtitle,
            )
            for entry in c.program
        ],
        transit=c.transit,
        parking=c.parking,
        website_url=c.website_url,
        cancel_reason=c.cancel_reason,
        published_at=event.published_at,
        favorite_count=event.favorite_count,
        source=_source(event.source),
        version=event.version,
    )


def _summary(row: ModEventRow) -> api.ModEventSummary:
    item = row.summary
    return api.ModEventSummary(
        id=item.id,
        name=item.name,
        status=api.ModEventStatus(row.status.value),
        start_date=item.start_date,
        end_date=item.end_date,
        place=item.place,
        city=item.city,
        category_id=item.category_id,
        favorite_count=item.favorite_count,
        source=_source(item.source),
        version=item.version,
    )


def _parse_version(if_match: str | None) -> int | None:
    """`If-Match: "3"`, `W/"3"` or `3` → 3; anything else is no usable version."""
    if if_match is None:
        return None
    value = if_match.strip().removeprefix("W/").strip('"')
    return int(value) if value.isdigit() else None


@router.get("", operation_id="listModEvents", response_model=api.ModEventList)
async def list_mod_events(
    deps: Deps,
    principal: CurrentPrincipal,
    status: api.ModEventStatus | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    ids: Annotated[str | None, Query(max_length=3700)] = None,
) -> api.ModEventList:
    """Events of the caller's region."""
    id_set: frozenset[UUID] | None = None
    if ids is not None:
        try:
            id_set = frozenset(UUID(part) for part in ids.split(",") if part)
        except ValueError:
            raise InvalidInputError({"ids": "invalid_uuid"}) from None
        if len(id_set) > 100:
            raise InvalidInputError({"ids": "too_many"})
    rows = await deps.list_mod_events(
        principal,
        status=ModStatus(status.root) if status else None,
        query=q,
        ids=id_set,
    )
    return api.ModEventList(items=[_summary(row) for row in rows])


@router.post(
    "",
    operation_id="createModEvent",
    status_code=201,
    response_model=api.ModEventDetail,
)
async def create_mod_event(
    deps: Deps, principal: CurrentPrincipal, body: api.ModEventCreate, response: Response
) -> api.ModEventDetail:
    """Create a draft in the caller's region."""
    content = EventContent(name=body.name)
    changes = _changes(body)
    changes.pop("name", None)
    view = await deps.create_mod_event(principal, _with(content, changes))
    response.headers.update(_etag(view.event.version))
    return _detail(view)


def _with(content: EventContent, changes: dict[str, object]) -> EventContent:
    return replace(content, **changes)  # type: ignore[arg-type]


@router.get("/{event_id}", operation_id="getModEvent", response_model=api.ModEventDetail)
async def get_mod_event(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID, response: Response
) -> api.ModEventDetail:
    """One event for editing."""
    view = await deps.get_mod_event(principal, event_id)
    response.headers.update(_etag(view.event.version))
    return _detail(view)


@router.patch(
    "/{event_id}",
    operation_id="updateModEvent",
    response_model=api.ModEventDetail,
    responses={428: {}},
)
async def update_mod_event(
    deps: Deps,
    principal: CurrentPrincipal,
    event_id: UUID,
    body: api.ModEventPatch,
    response: Response,
    if_match: Annotated[str | None, Header(max_length=20)] = None,
) -> api.ModEventDetail | Response:
    """Merge-patch the event under the optimistic lock."""
    version = _parse_version(if_match)
    if version is None:
        return error_response(
            428, "precondition_required", "Bitte lade das Fest neu und versuche es erneut."
        )
    view = await deps.update_mod_event(principal, event_id, _changes(body), version)
    response.headers.update(_etag(view.event.version))
    return _detail(view)


@router.delete("/{event_id}", operation_id="deleteModEvent", status_code=204)
async def delete_mod_event(deps: Deps, principal: CurrentPrincipal, event_id: UUID) -> Response:
    """Soft-delete the event."""
    await deps.delete_mod_event(principal, event_id)
    return Response(status_code=204)


@router.post(
    "/{event_id}/publish", operation_id="publishModEvent", response_model=api.ModEventDetail
)
async def publish_mod_event(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID, response: Response
) -> api.ModEventDetail:
    """Publish a draft."""
    view = await deps.publish_mod_event(principal, event_id)
    response.headers.update(_etag(view.event.version))
    return _detail(view)


@router.post(
    "/{event_id}/unpublish", operation_id="unpublishModEvent", response_model=api.ModEventDetail
)
async def unpublish_mod_event(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID, response: Response
) -> api.ModEventDetail:
    """Withdraw a published event."""
    view = await deps.unpublish_mod_event(principal, event_id)
    response.headers.update(_etag(view.event.version))
    return _detail(view)


@router.post("/{event_id}/cancel", operation_id="cancelModEvent", response_model=api.ModEventDetail)
async def cancel_mod_event(
    deps: Deps,
    principal: CurrentPrincipal,
    event_id: UUID,
    response: Response,
    body: api.CancelRequest | None = None,
) -> api.ModEventDetail:
    """Cancel a published event."""
    view = await deps.cancel_mod_event(principal, event_id, body.reason if body else None)
    response.headers.update(_etag(view.event.version))
    return _detail(view)
