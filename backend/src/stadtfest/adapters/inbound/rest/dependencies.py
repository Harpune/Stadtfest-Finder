"""Typed access to the use cases wired in the composition root (`app.state.container`)."""

from __future__ import annotations

from typing import Annotated, Protocol

from fastapi import Depends, Request
from redis.asyncio import Redis

from stadtfest.application.events.use_cases import (
    CountEvents,
    GetPublicEvent,
    ListActiveCategories,
    SearchEvents,
)
from stadtfest.application.geocoding.use_cases import Geocode, ReverseGeocode
from stadtfest.application.health.check_readiness import CheckReadiness
from stadtfest.application.identity.use_cases import Authenticate, DeleteAccount, GetMe, UpdateMe


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


def container(request: Request) -> RestDependencies:
    """Return the process-wide dependency container."""
    deps: RestDependencies = request.app.state.container
    return deps


Deps = Annotated[RestDependencies, Depends(container)]
