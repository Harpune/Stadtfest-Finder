"""Friends (R12): `/v1/me/friend-link`, `/v1/friend-links/{token}`, `/v1/me/friends`."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.application.collections.friends import FriendLinkView, FriendView
from stadtfest.generated import models as api

router = APIRouter(tags=["friends"])

Token = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{22}$")]


def _link(link: FriendLinkView) -> api.FriendLink:
    return api.FriendLink(token=link.token, created_at=link.created_at)


def _friend(friend: FriendView) -> api.Friend:
    return api.Friend(
        id=friend.id,
        first_name=friend.first_name,
        last_name=friend.last_name,
        since=friend.since,
    )


@router.get("/v1/me/friend-link", operation_id="getFriendLink", response_model=api.FriendLink)
async def get_friend_link(deps: Deps, principal: CurrentPrincipal) -> api.FriendLink:
    """Return the caller's link token (created on first use)."""
    return _link(await deps.get_friend_link(principal))


@router.post(
    "/v1/me/friend-link/rotate", operation_id="rotateFriendLink", response_model=api.FriendLink
)
async def rotate_friend_link(deps: Deps, principal: CurrentPrincipal) -> api.FriendLink:
    """Replace the token; the old link stops working."""
    return _link(await deps.rotate_friend_link(principal))


@router.get(
    "/v1/friend-links/{token}",
    operation_id="getFriendLinkOwner",
    response_model=api.FriendLinkOwner,
)
async def get_friend_link_owner(
    deps: Deps, principal: CurrentPrincipal, token: Token
) -> api.FriendLinkOwner:
    """First name and initial of the link owner."""
    owner = await deps.look_up_friend_link(principal, token)
    return api.FriendLinkOwner(
        owner=api.Owner(first_name=owner.first_name, last_name_initial=owner.last_name_initial)
    )


@router.post(
    "/v1/friend-links/{token}/accept",
    operation_id="acceptFriendLink",
    response_model=api.Friend,
    status_code=201,
)
async def accept_friend_link(deps: Deps, principal: CurrentPrincipal, token: Token) -> api.Friend:
    """Become friends with the link owner."""
    return _friend(await deps.accept_friend_link(principal, token))


@router.get("/v1/me/friends", operation_id="listFriends", response_model=api.FriendList)
async def list_friends(deps: Deps, principal: CurrentPrincipal) -> api.FriendList:
    """The caller's friends, alphabetically."""
    return api.FriendList(items=[_friend(f) for f in await deps.list_friends(principal)])


@router.delete("/v1/me/friends/{user_id}", operation_id="removeFriend", status_code=204)
async def remove_friend(deps: Deps, principal: CurrentPrincipal, user_id: UUID) -> Response:
    """End the friendship in both directions."""
    await deps.remove_friend(principal, user_id)
    return Response(status_code=204)
