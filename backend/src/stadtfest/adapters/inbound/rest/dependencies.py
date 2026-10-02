"""Typed access to the use cases wired in the composition root (`app.state.container`)."""

from __future__ import annotations

from typing import Annotated, Protocol

from fastapi import Depends, Request
from redis.asyncio import Redis

from stadtfest.adapters.outbound.storage.urls import ImageUrls
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
from stadtfest.application.geocoding.use_cases import (
    Geocode,
    ReverseGeocode,
    ReverseGeocodeEventLocation,
)
from stadtfest.application.health.check_readiness import CheckReadiness
from stadtfest.application.identity.use_cases import Authenticate, DeleteAccount, GetMe, UpdateMe
from stadtfest.application.moderation.images import (
    AttachImage,
    CreateUpload,
    OrderImages,
    RemoveImage,
    RetryImage,
)
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
    reverse_geocode_event_location: ReverseGeocodeEventLocation
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
    image_urls: ImageUrls
    create_upload: CreateUpload
    attach_image: AttachImage
    order_images: OrderImages
    remove_image: RemoveImage
    retry_image: RetryImage


def container(request: Request) -> RestDependencies:
    """Return the process-wide dependency container."""
    deps: RestDependencies = request.app.state.container
    return deps


Deps = Annotated[RestDependencies, Depends(container)]
