"""Invitations (R14): event invitation, answers, received invitations and links."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.adapters.inbound.rest.events import summary_fields
from stadtfest.application.collections.invitations import (
    InvitationPersonView,
    InvitationView,
    InviteeView,
    ReceivedInvitationView,
)
from stadtfest.domain.collections.invitations import InviteeStatus
from stadtfest.generated import models as api

router = APIRouter(tags=["invitations"])

Token = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{22}$")]


def person(view: InvitationPersonView) -> api.InvitationPerson:
    """Map a host or invitee."""
    return api.InvitationPerson(id=view.id, first_name=view.first_name, last_name=view.last_name)


def _invitee(view: InviteeView) -> api.Invitee:
    return api.Invitee(
        person=person(view.person),
        status=api.InviteeStatus(view.status.value),
        invited_at=view.invited_at,
        responded_at=view.responded_at,
    )


def _host(view: InvitationView) -> api.HostInvitation:
    return api.HostInvitation(
        id=view.id,
        event=api.EventSummary(**summary_fields(view.event)),
        message=view.message,
        invitees=[_invitee(i) for i in view.invitees],
        last_reminder_at=view.last_reminder_at,
    )


def _received(view: ReceivedInvitationView) -> api.ReceivedInvitation:
    invitation = view.invitation
    return api.ReceivedInvitation(
        id=invitation.id,
        event=api.EventSummary(**summary_fields(invitation.event)),
        host=person(invitation.host),
        message=invitation.message,
        created_at=invitation.created_at,
        status=api.InviteeStatus(view.status.value),
        others=[_invitee(i) for i in view.others],
    )


@router.get(
    "/v1/events/{event_id}/invitation",
    operation_id="getHostInvitation",
    response_model=api.HostInvitation,
)
async def get_host_invitation(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID
) -> api.HostInvitation:
    """The caller's invitation as host."""
    return _host(await deps.get_host_invitation(principal, event_id))


@router.post(
    "/v1/events/{event_id}/invitation/invitees",
    operation_id="inviteFriends",
    response_model=api.HostInvitation,
    status_code=201,
)
async def invite_friends(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID, body: api.InviteRequest
) -> api.HostInvitation:
    """Invite friends."""
    message = body.message.root if body.message is not None else None
    return _host(await deps.invite_friends(principal, event_id, body.user_ids, message))


@router.post(
    "/v1/events/{event_id}/invitation/link",
    operation_id="createInvitationLink",
    response_model=api.InvitationLink,
)
async def create_invitation_link(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID
) -> api.InvitationLink:
    """Link token for friends without the app."""
    return api.InvitationLink(token=await deps.create_invitation_link(principal, event_id))


@router.post(
    "/v1/invitations/{invitation_id}/reminders",
    operation_id="remindInvitees",
    response_model=api.ReminderResult,
    status_code=202,
)
async def remind_invitees(
    deps: Deps, principal: CurrentPrincipal, invitation_id: UUID
) -> api.ReminderResult:
    """Remind open invitees."""
    return api.ReminderResult(reminded=await deps.remind_invitees(principal, invitation_id))


@router.put(
    "/v1/invitations/{invitation_id}/response",
    operation_id="respondToInvitation",
    response_model=api.ReceivedInvitation,
)
async def respond_to_invitation(
    deps: Deps, principal: CurrentPrincipal, invitation_id: UUID, body: api.InvitationResponse
) -> api.ReceivedInvitation:
    """Accept, decline or reset."""
    status = InviteeStatus(body.status.root)
    return _received(await deps.respond_to_invitation(principal, invitation_id, status))


@router.get(
    "/v1/me/invitations",
    operation_id="listReceivedInvitations",
    response_model=list[api.ReceivedInvitation],
)
async def list_received_invitations(
    deps: Deps, principal: CurrentPrincipal
) -> list[api.ReceivedInvitation]:
    """Received invitations, newest first."""
    return [_received(item) for item in await deps.list_received_invitations(principal)]


@router.get(
    "/v1/me/invitations/{invitation_id}",
    operation_id="getReceivedInvitation",
    response_model=api.ReceivedInvitation,
)
async def get_received_invitation(
    deps: Deps, principal: CurrentPrincipal, invitation_id: UUID
) -> api.ReceivedInvitation:
    """A received invitation."""
    return _received(await deps.get_received_invitation(principal, invitation_id))


@router.get(
    "/v1/invitation-links/{token}",
    operation_id="getInvitationLinkPreview",
    response_model=api.InvitationLinkPreview,
)
async def get_invitation_link_preview(
    deps: Deps, principal: CurrentPrincipal, token: Token
) -> api.InvitationLinkPreview:
    """Host and event of a link."""
    preview = await deps.look_up_invitation_link(principal, token)
    return api.InvitationLinkPreview(
        host=api.Host(
            first_name=preview.host.first_name,
            last_name_initial=preview.host.last_name_initial,
        ),
        event=api.EventSummary(**summary_fields(preview.event)),
        own=preview.own,
    )


@router.post(
    "/v1/invitation-links/{token}/accept",
    operation_id="acceptInvitationLink",
    response_model=api.ReceivedInvitation,
    status_code=201,
)
async def accept_invitation_link(
    deps: Deps, principal: CurrentPrincipal, token: Token
) -> api.ReceivedInvitation:
    """Befriend the host and become an invitee."""
    return _received(await deps.accept_invitation_link(principal, token))
