"""`/v1/mod/uploads` and `/v1/mod/events/{id}/images`: event images for moderators (R08).

Thin adapter: parse and translate; authorization and rules live in the use cases.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response

from stadtfest.adapters.inbound.rest.auth import CurrentPrincipal
from stadtfest.adapters.inbound.rest.dependencies import Deps
from stadtfest.adapters.inbound.rest.events import image_model
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.domain.events.images import EventImage, ImageStatus
from stadtfest.generated import models as api

router = APIRouter(prefix="/v1/mod", tags=["moderation"])


def mod_image(image: EventImage, urls: ImageUrls) -> api.ModImage:
    """API model of an image; variant URLs only once it is ready."""
    ready = image.status is ImageStatus.READY
    return api.ModImage(
        id=image.id,
        status=api.ModImageStatus(image.status.value),
        position=image.position,
        image=image_model(urls.view(image.id, image.width, image.height)) if ready else None,
    )


@router.post("/uploads", operation_id="createModUpload", status_code=201, response_model=api.Upload)
async def create_upload(
    deps: Deps, principal: CurrentPrincipal, body: api.UploadRequest
) -> api.Upload:
    """Sign a direct upload of exactly this type and size."""
    slot = await deps.create_upload(principal, body.content_type.root, body.size_bytes)
    return api.Upload(
        upload_id=slot.upload_id,
        url=slot.url,
        method="PUT",
        headers=slot.headers,
        expires_at=slot.expires_at,
    )


@router.post(
    "/events/{event_id}/images",
    operation_id="attachModEventImage",
    status_code=201,
    response_model=api.ModImage,
)
async def attach_image(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID, body: api.AttachImageRequest
) -> api.ModImage:
    """Attach an uploaded file; processing follows in the background."""
    image = await deps.attach_image(principal, event_id, body.upload_id, body.position)
    return mod_image(image, deps.image_urls)


@router.put(
    "/events/{event_id}/images/order",
    operation_id="orderModEventImages",
    response_model=list[api.ModImage],
)
async def order_images(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID, body: api.ImageOrderRequest
) -> list[api.ModImage]:
    """Set the complete order; the first image is the cover."""
    images = await deps.order_images(principal, event_id, body.image_ids)
    return [mod_image(image, deps.image_urls) for image in images]


@router.delete(
    "/events/{event_id}/images/{image_id}", operation_id="deleteModEventImage", status_code=204
)
async def delete_image(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID, image_id: UUID
) -> Response:
    """Remove the image; its files are deleted in the background."""
    await deps.remove_image(principal, event_id, image_id)
    return Response(status_code=204)


@router.post(
    "/events/{event_id}/images/{image_id}/retry",
    operation_id="retryModEventImage",
    status_code=202,
    response_model=api.ModImage,
)
async def retry_image(
    deps: Deps, principal: CurrentPrincipal, event_id: UUID, image_id: UUID
) -> api.ModImage:
    """Process a failed image again."""
    image = await deps.retry_image(principal, event_id, image_id)
    return mod_image(image, deps.image_urls)
