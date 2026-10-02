"""REST adapter tests for uploads and event images (fakes, no database or storage)."""

from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from stadtfest.adapters.inbound.rest import mod_events, mod_images
from stadtfest.adapters.inbound.rest.auth import optional_principal
from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.identity.claims import ClaimMapping
from stadtfest.application.identity.use_cases import Authenticate
from stadtfest.application.moderation.images import (
    AttachImage,
    CreateUpload,
    OrderImages,
    ProcessImage,
    RemoveImage,
    RetryImage,
)
from stadtfest.application.moderation.ports import ModRegion
from stadtfest.application.moderation.use_cases import CreateModEvent, GetModEvent
from stadtfest.domain.events.images import upload_key
from stadtfest.domain.events.region import Region
from tests.fakes import (
    FakeAccountResolver,
    FakeCache,
    FakeDeletedAccounts,
    FakeImageProcessor,
    FakeImageRepository,
    FakeManagedEventRepository,
    FakeModRegions,
    FakeObjectStorage,
    FakeTokenVerifier,
    FixedClock,
)

OSTALB = ModRegion(uuid4(), Region("ostalb", "Ostalb", frozenset({"73430"})))
MOD = {"Authorization": "Bearer mod"}
USER = {"Authorization": "Bearer user"}


class Api:
    def __init__(self) -> None:
        verifier = FakeTokenVerifier(
            {
                "mod": {"sub": "m", "realm_access": {"roles": ["moderator"]}, "region": "ostalb"},
                "user": {"sub": "u", "realm_access": {"roles": ["user"]}},
            }
        )
        events = FakeManagedEventRepository()
        self.images = FakeImageRepository(images=events.images)
        self.storage = FakeObjectStorage()
        cache = FakeCache()
        accounts = FakeAccountResolver()
        base = (events, FakeModRegions({"ostalb": OSTALB}), FixedClock(date(2026, 10, 1)))
        app = FastAPI(dependencies=[Depends(optional_principal)])
        register_error_handlers(app)
        app.include_router(mod_events.router)
        app.include_router(mod_images.router)
        app.state.container = SimpleNamespace(
            authenticate=Authenticate(
                verifier, ClaimMapping("realm_access.roles", "region"), FakeDeletedAccounts()
            ),
            image_urls=ImageUrls("https://img.test/bucket/"),
            get_mod_event=GetModEvent(*base),
            create_mod_event=CreateModEvent(*base, accounts),
            create_upload=CreateUpload(*base, accounts, self.images, self.storage),
            attach_image=AttachImage(*base, self.images, cache, accounts, self.storage),
            order_images=OrderImages(*base, self.images, cache),
            remove_image=RemoveImage(*base, self.images, cache),
            retry_image=RetryImage(*base, self.images, cache, self.storage),
        )
        self.process = ProcessImage(self.images, self.storage, FakeImageProcessor(), cache)
        self.client = TestClient(app)

    def event(self) -> str:
        response = self.client.post("/v1/mod/events", json={"name": "Herbstfest"}, headers=MOD)
        return str(response.json()["id"])

    def upload(self, content: bytes = b"IMG") -> str:
        response = self.client.post(
            "/v1/mod/uploads",
            json={"contentType": "image/jpeg", "sizeBytes": len(content)},
            headers=MOD,
        )
        assert response.status_code == 201
        upload_id = str(response.json()["uploadId"])
        self.storage.objects[upload_key(UUID(upload_id))] = content
        return upload_id

    def attach(self, event_id: str) -> str:
        response = self.client.post(
            f"/v1/mod/events/{event_id}/images", json={"uploadId": self.upload()}, headers=MOD
        )
        assert response.status_code == 201
        return str(response.json()["id"])


@pytest.fixture
def api() -> Api:
    return Api()


def test_upload_slot(api: Api) -> None:
    response = api.client.post(
        "/v1/mod/uploads", json={"contentType": "image/webp", "sizeBytes": 2048}, headers=MOD
    )

    assert response.status_code == 201
    body = response.json()
    assert body["method"] == "PUT"
    assert body["headers"] == {"Content-Type": "image/webp"}
    assert body["url"].startswith("https://s3.test/bucket/uploads/")


def test_upload_limits_and_role(api: Api) -> None:
    too_big = api.client.post(
        "/v1/mod/uploads",
        json={"contentType": "image/jpeg", "sizeBytes": 10 * 1024 * 1024 + 1},
        headers=MOD,
    )
    assert too_big.status_code == 422
    forbidden = api.client.post(
        "/v1/mod/uploads", json={"contentType": "image/jpeg", "sizeBytes": 1}, headers=USER
    )
    assert forbidden.status_code == 403


async def test_attach_process_and_show_in_the_event(api: Api) -> None:
    event_id = api.event()
    image_id = api.attach(event_id)

    processing = api.client.get(f"/v1/mod/events/{event_id}", headers=MOD).json()["images"]
    assert processing == [{"id": image_id, "status": "processing", "position": 0, "image": None}]

    await api.process(UUID(image_id))
    ready = api.client.get(f"/v1/mod/events/{event_id}", headers=MOD).json()["images"][0]
    assert ready["status"] == "ready"
    assert ready["image"] == {
        "url": f"https://img.test/bucket/public/images/{image_id}/full.webp",
        "cardUrl": f"https://img.test/bucket/public/images/{image_id}/card.webp",
        "thumbUrl": f"https://img.test/bucket/public/images/{image_id}/thumb.webp",
        "jpegUrl": f"https://img.test/bucket/public/images/{image_id}/full.jpg",
        "width": 1600,
        "height": 1200,
    }


def test_attach_without_uploaded_file(api: Api) -> None:
    event_id = api.event()
    upload_id = api.upload()
    api.storage.objects.clear()

    response = api.client.post(
        f"/v1/mod/events/{event_id}/images", json={"uploadId": upload_id}, headers=MOD
    )

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_upload"


def test_order_and_delete(api: Api) -> None:
    event_id = api.event()
    first, second = api.attach(event_id), api.attach(event_id)

    ordered = api.client.put(
        f"/v1/mod/events/{event_id}/images/order",
        json={"imageIds": [second, first]},
        headers=MOD,
    )
    assert [image["id"] for image in ordered.json()] == [second, first]
    incomplete = api.client.put(
        f"/v1/mod/events/{event_id}/images/order", json={"imageIds": [first]}, headers=MOD
    )
    assert incomplete.status_code == 422

    deleted = api.client.delete(f"/v1/mod/events/{event_id}/images/{second}", headers=MOD)
    assert deleted.status_code == 204
    again = api.client.delete(f"/v1/mod/events/{event_id}/images/{second}", headers=MOD)
    assert again.status_code == 404


def test_retry_only_failed_images(api: Api) -> None:
    event_id = api.event()
    image_id = api.attach(event_id)

    response = api.client.post(f"/v1/mod/events/{event_id}/images/{image_id}/retry", headers=MOD)

    assert response.status_code == 409
    assert response.json()["error"] == "not_retryable"
