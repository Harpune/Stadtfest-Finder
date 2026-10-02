from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from stadtfest.application.moderation.image_ports import UploadRecord
from stadtfest.application.moderation.images import (
    AttachImage,
    CreateUpload,
    DeleteImageFiles,
    OrderImages,
    ProcessImage,
    PurgeImages,
    RemoveImage,
    RetryImage,
)
from stadtfest.application.moderation.ports import ModRegion
from stadtfest.application.moderation.use_cases import GetModEvent
from stadtfest.application.outbox.ports import OutboxMessage
from stadtfest.application.outbox.use_cases import HandleDomainEvent
from stadtfest.application.shared.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
    ServiceUnavailableError,
)
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.images import (
    EventImage,
    ImageStatus,
    all_variant_keys,
    upload_key,
)
from stadtfest.domain.events.maintenance import EventContent, ManagedEvent
from stadtfest.domain.events.region import Region
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import (
    FakeAccountResolver,
    FakeCache,
    FakeEventFavorites,
    FakeImageProcessor,
    FakeImageRepository,
    FakeManagedEventRepository,
    FakeModRegions,
    FakeObjectStorage,
    FixedClock,
)

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
OSTALB = ModRegion(uuid4(), Region("ostalb", "Ostalb", frozenset({"73430"})))
ULM = ModRegion(uuid4(), Region("ulm", "Ulm", frozenset({"89073"})))
MODERATOR = Principal("sub-mod", frozenset({Role.USER, Role.MODERATOR}), "ostalb")
OTHER_MODERATOR = Principal("sub-other", frozenset({Role.USER, Role.MODERATOR}), "ostalb")
USER = Principal("sub-user", frozenset({Role.USER}))


class Setup:
    def __init__(self) -> None:
        self.events = FakeManagedEventRepository()
        self.images = FakeImageRepository(images=self.events.images)
        self.storage = FakeObjectStorage()
        self.cache = FakeCache()
        regions = FakeModRegions({"ostalb": OSTALB, "ulm": ULM})
        clock = FixedClock(date(2026, 10, 1))
        accounts = FakeAccountResolver()
        base = (self.events, regions, clock)
        self.get = GetModEvent(*base)
        self.create_upload = CreateUpload(
            *base, accounts, self.images, self.storage, now=lambda: NOW
        )
        self.attach = AttachImage(
            *base, self.images, self.cache, accounts, self.storage, now=lambda: NOW
        )
        self.order = OrderImages(*base, self.images, self.cache)
        self.remove = RemoveImage(*base, self.images, self.cache)
        self.retry = RetryImage(*base, self.images, self.cache, self.storage)
        self.process = ProcessImage(self.images, self.storage, FakeImageProcessor(), self.cache)
        self.delete_files = DeleteImageFiles(self.storage)
        self.purge = PurgeImages(self.images, self.storage, now=lambda: NOW)

    def event(self, region: ModRegion = OSTALB) -> ManagedEvent:
        event = ManagedEvent(uuid4(), region.id, EventStatus.DRAFT, EventContent(name="Fest"))
        self.events.events[event.id] = event
        return event

    async def uploaded(self, content: bytes = b"IMG-data") -> UUID:
        slot = await self.create_upload(MODERATOR, "image/jpeg", len(content))
        self.storage.objects[upload_key(slot.upload_id)] = content
        return slot.upload_id

    async def attached(self, event: ManagedEvent, content: bytes = b"IMG-data") -> EventImage:
        return await self.attach(MODERATOR, event.id, await self.uploaded(content), None)


@pytest.fixture
def s() -> Setup:
    return Setup()


# --- upload (R08-US1) --------------------------------------------------------------------


async def test_upload_slot_is_signed_for_type_and_size_for_10_minutes(s: Setup) -> None:
    slot = await s.create_upload(MODERATOR, "image/png", 2048)

    assert s.storage.signed == [(upload_key(slot.upload_id), "image/png", 2048, 600)]
    assert slot.headers == {"Content-Type": "image/png"}
    assert slot.expires_at == NOW + timedelta(minutes=10)
    assert s.images.uploads[slot.upload_id].consumed_at is None


async def test_upload_rejects_other_types_and_sizes(s: Setup) -> None:
    with pytest.raises(InvalidInputError) as error:
        await s.create_upload(MODERATOR, "image/gif", 20 * 1024 * 1024)
    assert error.value.fields == {"contentType": "unsupported_type", "sizeBytes": "too_large"}


async def test_upload_needs_the_moderator_role(s: Setup) -> None:
    with pytest.raises(ForbiddenError):
        await s.create_upload(USER, "image/jpeg", 10)


async def test_upload_reports_an_unavailable_storage(s: Setup) -> None:
    s.storage.unavailable = True
    with pytest.raises(ServiceUnavailableError):
        await s.create_upload(MODERATOR, "image/jpeg", 10)


async def test_attach_appends_consumes_the_upload_and_writes_the_event(s: Setup) -> None:
    event = s.event()
    first = await s.attached(event)
    second = await s.attached(event)

    assert (first.position, second.position) == (0, 1)
    assert second.status is ImageStatus.PROCESSING
    assert s.images.uploads[second.upload_id].consumed_at == NOW  # type: ignore[index]
    assert [kind for kind, _ in s.images.outbox] == ["image.uploaded", "image.uploaded"]
    view = await s.get(MODERATOR, event.id)
    assert [image.id for image in view.images] == [first.id, second.id]


async def test_attach_at_a_position_moves_the_others_back(s: Setup) -> None:
    event = s.event()
    first = await s.attached(event)
    cover = await s.attach(MODERATOR, event.id, await s.uploaded(), 0)

    assert [i.id for i in await s.images.list_for_event(event.id)] == [cover.id, first.id]


@pytest.mark.parametrize("problem", ["unknown", "not_uploaded", "used", "foreign"])
async def test_attach_rejects_invalid_uploads(s: Setup, problem: str) -> None:
    event = s.event()
    upload_id = await s.uploaded()
    if problem == "unknown":
        upload_id = uuid4()
    elif problem == "not_uploaded":
        s.storage.objects.clear()
    elif problem == "used":
        await s.attach(MODERATOR, event.id, upload_id, None)
    principal = OTHER_MODERATOR if problem == "foreign" else MODERATOR

    with pytest.raises(InvalidInputError) as error:
        await s.attach(principal, event.id, upload_id, None)
    assert error.value.code == "invalid_upload"


async def test_at_most_12_images(s: Setup) -> None:
    event = s.event()
    for _ in range(12):
        await s.attached(event)
    with pytest.raises(InvalidInputError) as error:
        await s.attached(event)
    assert error.value.code == "too_many_images"


async def test_images_of_other_regions_look_unknown(s: Setup) -> None:
    event = s.event(ULM)
    with pytest.raises(NotFoundError):
        await s.attach(MODERATOR, event.id, await s.uploaded(), None)


# --- processing (R08-US2) ----------------------------------------------------------------


async def test_processing_creates_variants_and_deletes_the_original(s: Setup) -> None:
    event = s.event()
    image = await s.attached(event)

    assert await s.process(image.id) is ImageStatus.READY

    stored = await s.images.get(image.id)
    assert stored is not None
    assert (stored.status, stored.width, stored.height) == (ImageStatus.READY, 1600, 1200)
    assert set(s.storage.objects) == set(all_variant_keys(image.id))
    assert s.storage.content_types[f"public/images/{image.id}/full.webp"] == "image/webp"
    assert await s.cache.generation("catalog") == 1
    assert await s.process(image.id) is None  # delivered twice: nothing happens


async def test_unsupported_content_fails_and_keeps_the_original(s: Setup) -> None:
    event = s.event()
    image = await s.attached(event, b"GIF89a")

    assert await s.process(image.id) is ImageStatus.FAILED
    assert set(s.storage.objects) == {upload_key(image.upload_id)}  # type: ignore[arg-type]


async def test_failed_images_can_be_retried(s: Setup) -> None:
    event = s.event()
    image = await s.attached(event)
    s.storage.unavailable = True
    assert await s.process(image.id) is ImageStatus.FAILED
    s.storage.unavailable = False

    retried = await s.retry(MODERATOR, event.id, image.id)

    assert retried.status is ImageStatus.PROCESSING
    assert s.images.outbox[-1][0] == "image.uploaded"
    assert await s.process(image.id) is ImageStatus.READY


async def test_only_failed_images_with_their_upload_can_be_retried(s: Setup) -> None:
    event = s.event()
    image = await s.attached(event)
    with pytest.raises(ConflictError):
        await s.retry(MODERATOR, event.id, image.id)  # still processing
    await s.images.mark_failed(image.id)
    s.storage.objects.clear()
    with pytest.raises(ConflictError):
        await s.retry(MODERATOR, event.id, image.id)  # upload gone


async def test_image_removed_while_processing_leaves_no_files(s: Setup) -> None:
    event = s.event()
    image = await s.attached(event)
    data_key = upload_key(image.upload_id)  # type: ignore[arg-type]
    real_mark_ready = s.images.mark_ready

    async def removed_meanwhile(image_id: UUID, width: int, height: int) -> bool:
        await s.images.remove(event.id, image_id)
        return await real_mark_ready(image_id, width, height)

    s.images.mark_ready = removed_meanwhile  # type: ignore[method-assign]
    assert await s.process(image.id) is None
    assert data_key not in s.storage.objects
    assert not s.storage.objects


# --- order and removal (R08-US3) ---------------------------------------------------------


async def test_order_sets_the_cover(s: Setup) -> None:
    event = s.event()
    a, b, c = [await s.attached(event) for _ in range(3)]

    ordered = await s.order(MODERATOR, event.id, [c.id, a.id, b.id])

    assert [(i.id, i.position) for i in ordered] == [(c.id, 0), (a.id, 1), (b.id, 2)]
    assert await s.cache.generation("catalog") == 1


async def test_order_needs_the_complete_list(s: Setup) -> None:
    event = s.event()
    a, _ = [await s.attached(event) for _ in range(2)]
    with pytest.raises(InvalidInputError):
        await s.order(MODERATOR, event.id, [a.id])


async def test_remove_closes_the_gap_and_deletes_the_files_later(s: Setup) -> None:
    event = s.event()
    a, b = [await s.attached(event) for _ in range(2)]
    await s.process(a.id)

    await s.remove(MODERATOR, event.id, a.id)

    assert [(i.id, i.position) for i in await s.images.list_for_event(event.id)] == [(b.id, 0)]
    kind, payload = s.images.outbox[-1]
    assert (kind, payload["imageId"]) == ("image.removed", str(a.id))
    await s.delete_files(a.id, None)
    assert not any(key.startswith(f"public/images/{a.id}") for key in s.storage.objects)


async def test_remove_unknown_image_is_not_found(s: Setup) -> None:
    event = s.event()
    with pytest.raises(NotFoundError):
        await s.remove(MODERATOR, event.id, uuid4())


# --- consumers and clean-up --------------------------------------------------------------


async def test_image_events_reach_their_handlers() -> None:
    processed: list[UUID] = []
    deleted: list[tuple[UUID, UUID | None]] = []

    async def process(image_id: UUID) -> None:
        processed.append(image_id)

    async def delete(image_id: UUID, upload_id: UUID | None) -> None:
        deleted.append((image_id, upload_id))

    cache = FakeCache()
    handle = HandleDomainEvent(cache, FakeEventFavorites(), process, delete)
    image_id, upload_id = uuid4(), uuid4()
    await handle(OutboxMessage(uuid4(), "image.uploaded", {"imageId": str(image_id)}))
    await handle(
        OutboxMessage(
            uuid4(), "image.removed", {"imageId": str(image_id), "uploadId": str(upload_id)}
        )
    )

    assert processed == [image_id]
    assert deleted == [(image_id, upload_id)]
    assert await cache.generation("catalog") == 0


async def test_purge_removes_stale_uploads_and_images_of_deleted_events(s: Setup) -> None:
    event = s.event()
    image = await s.attached(event)
    await s.process(image.id)
    stale = UploadRecord(uuid4(), uuid4(), "image/jpeg", 10, NOW - timedelta(hours=25))
    fresh = UploadRecord(uuid4(), uuid4(), "image/jpeg", 10, NOW - timedelta(hours=1))
    for upload in (stale, fresh):
        s.images.uploads[upload.id] = upload
        s.storage.objects[upload_key(upload.id)] = b"IMG"
    s.images.deleted_event_ids.add(event.id)

    result = await s.purge()

    assert (result.uploads, result.images) == (1, 1)
    assert set(s.images.uploads) == {fresh.id}
    assert set(s.storage.objects) == {upload_key(fresh.id)}
    assert await s.images.list_for_event(event.id) == []
