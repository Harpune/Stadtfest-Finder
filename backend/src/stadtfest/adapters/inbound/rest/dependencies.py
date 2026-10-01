"""Typed access to the use cases wired in the composition root (`app.state.container`)."""

from __future__ import annotations

from typing import Annotated, Protocol

from fastapi import Depends, Request
from redis.asyncio import Redis

from stadtfest.application.collections.use_cases import (
    AddFavorite,
    IsFavorite,
    ListFavorites,
    RemoveFavorite,
)
from stadtfest.application.events.use_cases import (
    CountEvents,
    GetPublicEvent,
    ListActiveCategories,
    SearchEvents,
)
from stadtfest.application.geocoding.use_cases import Geocode, ReverseGeocode
from stadtfest.application.health.check_readiness import CheckReadiness
from stadtfest.application.identity.use_cases import Authenticate, DeleteAccount, GetMe, UpdateMe
from stadtfest.application.moderation.use_cases import (
    CancelModEvent,
    CreateModEvent,
    DeleteModEvent,
    GetModEvent,
    ListModEvents,
    PublishModEvent,
    UnpublishModEvent,
    UpdateModEvent,
)


class RestDependencies(Protocol):
    """What the REST adapter needs; satisfied structurally by `bootstrap.Container`."""

    redis: Redis
    check_readiness: CheckReadiness
    search_events: SearchEvents
    count_events: CountEvents
    get_public_event: GetPublicEvent
    list_active_categories: ListActiveCategories
    geocode: Geocode
    reverse_geocode: ReverseGeocode
    authenticate: Authenticate
    get_me: GetMe
    update_me: UpdateMe
    delete_account: DeleteAccount
    add_favorite: AddFavorite
    remove_favorite: RemoveFavorite
    list_favorites: ListFavorites
    is_favorite: IsFavorite
    list_mod_events: ListModEvents
    get_mod_event: GetModEvent
    create_mod_event: CreateModEvent
    update_mod_event: UpdateModEvent
    publish_mod_event: PublishModEvent
    unpublish_mod_event: UnpublishModEvent
    cancel_mod_event: CancelModEvent
    delete_mod_event: DeleteModEvent


def container(request: Request) -> RestDependencies:
    """Return the process-wide dependency container."""
    deps: RestDependencies = request.app.state.container
    return deps


Deps = Annotated[RestDependencies, Depends(container)]
