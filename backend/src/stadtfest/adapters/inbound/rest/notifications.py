"""`/v1/me/notifications`, `/v1/me/notification-settings`, `/v1/me/devices` (R11)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.application.notifications.ports import DevicePlatform, PushProvider
from stadtfest.application.notifications.use_cases import (
    HomeInput,
    NotificationItem,
    SettingsInput,
)
from stadtfest.domain.notifications.settings import NotificationSettings
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/me", tags=["notifications"])


def _notification(item: NotificationItem) -> api.Notification:
    return api.Notification(
        id=item.id,
        type=api.NotificationType(item.type.value),
        text=item.text,
        target=api.NotificationTarget(
            type="friend" if item.type.about_person else "event", id=item.subject_id
        ),
        read=item.read,
        created_at=item.created_at,
    )


@router.get("/notifications", operation_id="listNotifications", response_model=api.NotificationPage)
async def list_notifications(
    deps: Deps,
    principal: CurrentPrincipal,
    response: Response,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> api.NotificationPage:
    """Return one page, newest first; `X-Unread-Count` carries the badge number."""
    listing = await deps.list_notifications(principal, cursor, limit)
    response.headers["X-Unread-Count"] = str(listing.unread)
    return api.NotificationPage(
        items=[_notification(item) for item in listing.items], next_cursor=listing.next_cursor
    )


@router.post("/notifications/read-all", operation_id="markAllNotificationsRead", status_code=204)
async def mark_all_read(deps: Deps, principal: CurrentPrincipal) -> Response:
    """Mark all notifications read."""
    await deps.mark_all_notifications_read(principal)
    return Response(status_code=204)


@router.delete(
    "/notifications/{notification_id}", operation_id="deleteNotification", status_code=204
)
async def delete_notification(
    deps: Deps, principal: CurrentPrincipal, notification_id: UUID
) -> Response:
    """Delete one notification (idempotent)."""
    await deps.delete_notification(principal, notification_id)
    return Response(status_code=204)


@router.post(
    "/notifications/{notification_id}/read",
    operation_id="markNotificationRead",
    status_code=204,
)
async def mark_read(deps: Deps, principal: CurrentPrincipal, notification_id: UUID) -> Response:
    """Mark one notification read (idempotent)."""
    await deps.mark_notification_read(principal, notification_id)
    return Response(status_code=204)


def _settings(settings: NotificationSettings) -> api.NotificationSettings:
    home = settings.home
    return api.NotificationSettings(
        remind=settings.remind,
        remind_days_before=api.RemindDaysBefore(settings.remind_days_before),  # type: ignore[arg-type]
        near=settings.near,
        home=(
            api.Home(
                postal_code=home.postal_code,
                place_name=home.place_name,
                lat=home.location.lat,
                lon=home.location.lon,
            )
            if home
            else None
        ),
        near_radius_km=api.NearRadiusKm(settings.near_radius_km),
        change=settings.change,
        invite=settings.invite,
        rsvp=settings.rsvp,
    )


@router.get(
    "/notification-settings",
    operation_id="getNotificationSettings",
    response_model=api.NotificationSettings,
)
async def get_settings(deps: Deps, principal: CurrentPrincipal) -> api.NotificationSettings:
    """Return the settings (defaults until the first change)."""
    return _settings(await deps.get_notification_settings(principal))


@router.put(
    "/notification-settings",
    operation_id="updateNotificationSettings",
    response_model=api.NotificationSettings,
)
async def update_settings(
    deps: Deps, principal: CurrentPrincipal, body: api.NotificationSettingsUpdate
) -> api.NotificationSettings:
    """Replace the settings; the home is resolved to its ZIP code center."""
    update = SettingsInput(
        remind=body.remind,
        remind_days_before=body.remind_days_before.root,
        near=body.near,
        home=HomeInput(body.home.postal_code, body.home.place_name) if body.home else None,
        near_radius_km=body.near_radius_km.root,
        change=body.change,
        invite=body.invite,
        rsvp=body.rsvp,
    )
    return _settings(await deps.update_notification_settings(principal, update))


@router.post("/devices", operation_id="registerDevice", status_code=204)
async def register_device(
    deps: Deps, principal: CurrentPrincipal, body: api.DeviceRegistration
) -> Response:
    """Register the push token (idempotent)."""
    await deps.register_device(
        principal, body.token, DevicePlatform(body.platform.root), PushProvider(body.provider)
    )
    return Response(status_code=204)


@router.delete("/devices/{token}", operation_id="removeDevice", status_code=204)
async def remove_device(deps: Deps, principal: CurrentPrincipal, token: str) -> Response:
    """Remove the push token on sign-out (idempotent)."""
    await deps.remove_device(principal, token)
    return Response(status_code=204)
