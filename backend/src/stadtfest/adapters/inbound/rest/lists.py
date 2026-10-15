"""`/v1/lists`: shared lists with friends (R13)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.adapters.inbound.rest.events import summary_fields
from stadtfest.application.collections.lists import (
    ListEventView,
    ListMemberView,
    SharedListView,
)
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/lists", tags=["lists"])


def _member(member: ListMemberView) -> api.ListMember:
    return api.ListMember(id=member.id, first_name=member.first_name, last_name=member.last_name)


def _event(entry: ListEventView) -> api.ListEvent:
    return api.ListEvent(
        **summary_fields(entry.event),
        category_name=entry.category_name,
        emoji=entry.emoji,
        added_at=entry.added_at,
    )


def _list(view: SharedListView) -> api.SharedList:
    return api.SharedList(
        id=view.id,
        name=view.name,
        members=[_member(m) for m in view.members],
        events=[_event(e) for e in view.events],
    )


@router.get("", operation_id="listSharedLists", response_model=list[api.SharedListSummary])
async def list_shared_lists(deps: Deps, principal: CurrentPrincipal) -> list[api.SharedListSummary]:
    """The caller's lists, by next event."""
    return [
        api.SharedListSummary(
            id=item.list.id,
            name=item.list.name,
            event_count=len(item.list.events),
            members=[_member(m) for m in item.list.members],
            next_event=_event(item.next_event) if item.next_event else None,
        )
        for item in await deps.list_shared_lists(principal)
    ]


@router.post("", operation_id="createSharedList", response_model=api.SharedList, status_code=201)
async def create_shared_list(
    deps: Deps, principal: CurrentPrincipal, body: api.SharedListCreate
) -> api.SharedList:
    """Create a list with friends."""
    created = await deps.create_shared_list(principal, body.name.root, body.member_ids)
    return _list(created)


@router.get("/{list_id}", operation_id="getSharedList", response_model=api.SharedList)
async def get_shared_list(deps: Deps, principal: CurrentPrincipal, list_id: UUID) -> api.SharedList:
    """One list (members only)."""
    return _list(await deps.get_shared_list(principal, list_id))


@router.patch("/{list_id}", operation_id="renameSharedList", response_model=api.SharedList)
async def rename_shared_list(
    deps: Deps, principal: CurrentPrincipal, list_id: UUID, body: api.SharedListRename
) -> api.SharedList:
    """Rename a list."""
    return _list(await deps.rename_shared_list(principal, list_id, body.name.root))


@router.delete("/{list_id}", operation_id="deleteSharedList", status_code=204)
async def delete_shared_list(deps: Deps, principal: CurrentPrincipal, list_id: UUID) -> Response:
    """Delete a list for everyone."""
    await deps.delete_shared_list(principal, list_id)
    return Response(status_code=204)


@router.post("/{list_id}/members", operation_id="addSharedListMember", status_code=204)
async def add_member(
    deps: Deps, principal: CurrentPrincipal, list_id: UUID, body: api.SharedListMemberAdd
) -> Response:
    """Add a friend."""
    await deps.add_list_member(principal, list_id, body.user_id)
    return Response(status_code=204)


@router.delete(
    "/{list_id}/members/{user_id}", operation_id="removeSharedListMember", status_code=204
)
async def remove_member(
    deps: Deps, principal: CurrentPrincipal, list_id: UUID, user_id: UUID
) -> Response:
    """Remove a member or leave."""
    await deps.remove_list_member(principal, list_id, user_id)
    return Response(status_code=204)


@router.put("/{list_id}/events/{event_id}", operation_id="addSharedListEvent", status_code=204)
async def add_event(
    deps: Deps, principal: CurrentPrincipal, list_id: UUID, event_id: UUID
) -> Response:
    """Add an event."""
    await deps.add_list_event(principal, list_id, event_id)
    return Response(status_code=204)


@router.delete(
    "/{list_id}/events/{event_id}", operation_id="removeSharedListEvent", status_code=204
)
async def remove_event(
    deps: Deps, principal: CurrentPrincipal, list_id: UUID, event_id: UUID
) -> Response:
    """Remove an event."""
    await deps.remove_list_event(principal, list_id, event_id)
    return Response(status_code=204)
