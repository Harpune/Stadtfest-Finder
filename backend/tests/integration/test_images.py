"""Image round trip against SeaweedFS, PostgreSQL and Redis (R08).

Signed URL → PUT → attach → outbox → worker → variants public, EXIF gone, original deleted.
"""

from __future__ import annotations

import asyncio
import io
import json
import time
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from PIL import ExifTags, Image
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.core.container import DockerContainer

from stadtfest.adapters.outbound.cache.redis_cache import RedisCache
from stadtfest.adapters.outbound.imaging.pillow import PillowImageProcessor
from stadtfest.adapters.outbound.persistence.accounts import SqlUserRepository
from stadtfest.adapters.outbound.persistence.catalog import SqlCatalog
from stadtfest.adapters.outbound.persistence.images import SqlImageRepository
from stadtfest.adapters.outbound.persistence.models import EventRow, OutboxRow, UploadRow
from stadtfest.adapters.outbound.persistence.moderation import (
    SqlActiveCategories,
    SqlManagedEventRepository,
    SqlModRegionDirectory,
)
from stadtfest.adapters.outbound.persistence.outbox import SqlEventFavorites, SqlOutboxStore
from stadtfest.adapters.outbound.storage.s3 import S3Config, S3ObjectStorage
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.identity.use_cases import EnsureAccount
from stadtfest.application.moderation.images import (
    AttachImage,
    CreateUpload,
    DeleteImageFiles,
    ProcessImage,
    PurgeImages,
    RemoveImage,
)
from stadtfest.application.outbox.ports import OutboxMessage
from stadtfest.application.outbox.use_cases import HandleDomainEvent, RelayOutbox
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.images import ImageStatus, all_variant_keys, upload_key
from stadtfest.domain.events.maintenance import EventContent, ManagedEvent
from stadtfest.domain.identity.principal import Principal, Role
from tests.conftest import REPO_ROOT
from tests.integration.seed_support import load

pytestmark = pytest.mark.integration

SEAWEEDFS_IMAGE = "chrislusf/seaweedfs:4.00"  # same as infra/compose.dev.yaml
S3_CONFIG = REPO_ROOT / "infra" / "dev" / "seaweedfs" / "s3.json"
BUCKET = "stadtfest-images"
TODAY = date(2026, 9, 25)
MODERATOR = Principal("sub-image-mod", frozenset({Role.USER, Role.MODERATOR}), "ostalb")


@pytest.fixture(scope="module")
def s3_endpoint() -> Iterator[str]:
    container = (
        DockerContainer(SEAWEEDFS_IMAGE)
        .with_command(
            "server -dir=/data -s3 -s3.port=8333 -s3.config=/etc/seaweedfs/s3.json "
            "-master.volumeSizeLimitMB=64"
        )
        .with_volume_mapping(str(S3_CONFIG), "/etc/seaweedfs/s3.json", "ro")
        .with_exposed_ports(8333)
    )
    with container:
        endpoint = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8333)}"
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{endpoint}/healthz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        else:
            pytest.fail("SeaweedFS did not become ready")
        yield endpoint


@pytest.fixture(scope="module")
async def storage(s3_endpoint: str) -> AsyncIterator[S3ObjectStorage]:
    credentials = json.loads(S3_CONFIG.read_text())["identities"][0]["credentials"][0]
    storage = S3ObjectStorage(
        S3Config(
            endpoint_url=s3_endpoint,
            bucket=BUCKET,
            region="eu-central-1",
            access_key_id=credentials["accessKey"],
            secret_access_key=credentials["secretKey"],
        )
    )
    # SeaweedFS may need a moment after /healthz before the S3 gateway accepts buckets.
    for _ in range(20):
        try:
            await storage.ensure_bucket()
            break
        except Exception:  # noqa: BLE001
            await asyncio.sleep(0.5)
    yield storage
    await storage.aclose()


@pytest.fixture(scope="module")
async def engine(migrated_postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_url)
    await load(async_sessionmaker(engine), TODAY)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


class World:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        storage: S3ObjectStorage,
        cache: RedisCache,
        public_base: str,
    ) -> None:
        self.sessions = sessions
        self.storage = storage
        self.public_base = public_base
        self.urls = ImageUrls(public_base)
        self.events = SqlManagedEventRepository(sessions)
        self.images = SqlImageRepository(sessions)
        accounts = EnsureAccount(SqlUserRepository(sessions))
        mod = (self.events, SqlModRegionDirectory(sessions), _Clock())
        self.create_upload = CreateUpload(*mod, accounts, self.images, storage)
        self.attach = AttachImage(*mod, self.images, cache, accounts, storage)
        self.remove = RemoveImage(*mod, self.images, cache)
        self.process = ProcessImage(self.images, storage, PillowImageProcessor(), cache)
        self.handle = HandleDomainEvent(
            cache, SqlEventFavorites(sessions), self.process, DeleteImageFiles(storage)
        )
        self.relay = RelayOutbox(SqlOutboxStore(sessions), _Collect(self))
        self.purge = PurgeImages(self.images, storage)
        self.catalog = SqlCatalog(sessions, self.urls)
        self.received: list[OutboxMessage] = []

    async def deliver(self) -> None:
        """Relay the outbox and run the consumers like the worker does."""
        await self.relay()
        while self.received:
            await self.handle(self.received.pop(0))


class _Collect:
    def __init__(self, world: World) -> None:
        self._world = world

    async def enqueue_domain_event(self, message: OutboxMessage) -> None:
        self._world.received.append(message)


class _Clock:
    def today(self) -> date:
        return TODAY


@pytest.fixture
async def world(
    sessions: async_sessionmaker[AsyncSession],
    storage: S3ObjectStorage,
    redis_url: str,
    s3_endpoint: str,
) -> AsyncIterator[World]:
    redis = Redis.from_url(redis_url)
    # Earlier modules may have left undispatched outbox rows.
    async with sessions.begin() as session:
        await session.execute(
            update(OutboxRow)
            .where(OutboxRow.dispatched_at.is_(None))
            .values(dispatched_at=datetime.now(UTC))
        )
    yield World(sessions, storage, RedisCache(redis), f"{s3_endpoint}/{BUCKET}")
    await redis.aclose()


def _photo_with_gps() -> bytes:
    image = Image.new("RGB", (2400, 1600), (30, 120, 200))
    exif = Image.Exif()
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N"
    gps[ExifTags.GPS.GPSLatitude] = (48.0, 50.0, 12.0)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


async def _published_event(world: World) -> ManagedEvent:
    ostalb = await SqlModRegionDirectory(world.sessions).by_key("ostalb")
    assert ostalb is not None
    category = next(iter(await SqlActiveCategories(world.sessions).active_ids()))
    content = EventContent(
        name="Bilderfest",
        category_id=category,
        start_date=date(2026, 10, 17),
        end_date=date(2026, 10, 18),
        place="Festplatz",
        city="Aalen",
        postal_code="73430",
        lat=48.86,
        lon=10.1,
    ).with_defaults()
    event = ManagedEvent(uuid4(), ostalb.id, EventStatus.PUBLISHED, content)
    user = (await SqlUserRepository(world.sessions).get_or_create("sub-seed", "S", "S")).id
    await world.events.add(event, user)
    return event


async def _upload(world: World, content: bytes) -> UUID:
    slot = await world.create_upload(MODERATOR, "image/jpeg", len(content))
    async with httpx.AsyncClient() as client:
        response = await client.put(slot.url, content=content, headers=slot.headers)
    assert response.status_code == 200, response.text
    return slot.upload_id


async def test_round_trip_strips_metadata_and_publishes_variants(world: World) -> None:
    event = await _published_event(world)
    original = _photo_with_gps()
    upload_id = await _upload(world, original)
    assert await world.storage.exists(upload_key(upload_id))

    image = await world.attach(MODERATOR, event.id, upload_id, None)
    await world.deliver()

    stored = await world.images.get(image.id)
    assert stored is not None
    assert (stored.status, stored.width, stored.height) == (ImageStatus.READY, 1600, 1067)
    assert not await world.storage.exists(upload_key(upload_id))
    async with world.sessions() as session:
        assert await session.get(UploadRow, upload_id) is None
    # Variants are publicly readable without credentials and carry no EXIF.
    view = world.urls.view(image.id, stored.width, stored.height)
    async with httpx.AsyncClient() as client:
        for url in (view.url, view.thumb_url, view.card_url, view.jpeg_url):
            assert url is not None
            response = await client.get(url)
            assert response.status_code == 200
            assert "immutable" in response.headers.get("cache-control", "")
            assert not Image.open(io.BytesIO(response.content)).getexif()
        private = await client.get(f"{world.public_base}/{upload_key(upload_id)}")
        assert private.status_code in (403, 404)
    # The public catalog shows the cover.
    detail = await world.catalog.get_public(event.id, None)
    assert detail is not None
    assert [i.url for i in detail.images] == [view.url]


async def test_unsupported_content_fails(world: World) -> None:
    event = await _published_event(world)
    upload_id = await _upload(world, b"GIF89a" + b"\x00" * 64)

    image = await world.attach(MODERATOR, event.id, upload_id, None)
    await world.deliver()

    stored = await world.images.get(image.id)
    assert stored is not None
    assert stored.status is ImageStatus.FAILED


async def test_remove_deletes_the_files(world: World) -> None:
    event = await _published_event(world)
    image = await world.attach(MODERATOR, event.id, await _upload(world, _photo_with_gps()), None)
    await world.deliver()

    await world.remove(MODERATOR, event.id, image.id)
    await world.deliver()

    for key in all_variant_keys(image.id):
        assert not await world.storage.exists(key)


async def test_purge_removes_stale_uploads_and_images_of_deleted_events(world: World) -> None:
    event = await _published_event(world)
    image = await world.attach(MODERATOR, event.id, await _upload(world, _photo_with_gps()), None)
    await world.deliver()
    stale = await _upload(world, b"stale")
    async with world.sessions.begin() as session:
        await session.execute(
            update(UploadRow)
            .where(UploadRow.id == stale)
            .values(created_at=datetime.now(UTC) - timedelta(hours=25))
        )
        await session.execute(
            update(EventRow).where(EventRow.id == event.id).values(deleted_at=datetime.now(UTC))
        )

    result = await world.purge()

    assert result.uploads >= 1
    assert result.images >= 1
    assert not await world.storage.exists(upload_key(stale))
    assert not await world.storage.exists(all_variant_keys(image.id)[0])
    async with world.sessions() as session:
        assert await session.scalar(select(UploadRow.id).where(UploadRow.id == stale)) is None
