"""In-memory fake adapters for all ports (unit tests)."""

from __future__ import annotations

import asyncio
import copy
import dataclasses
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from stadtfest.application.ai_ingestion.ports import (
    DraftCandidate,
    FinderLimits,
    FinderResult,
    LlmUnavailableError,
    PageTool,
    SearchHit,
    SearchTool,
    WebSearchUnavailableError,
)
from stadtfest.application.collections.ports import FavoriteView
from stadtfest.application.events.criteria import PageCursor, SearchCriteria
from stadtfest.application.events.views import (
    CategoryView,
    EventCountView,
    EventDetailView,
    EventSummaryView,
)
from stadtfest.application.geocoding.ports import GeocodingUnavailableError, Place
from stadtfest.application.identity.ports import (
    Claims,
    DeletedAccountsUnavailableError,
    IdpUnavailableError,
    InvalidTokenError,
    JobQueueUnavailableError,
    UserRecord,
)
from stadtfest.application.moderation.categories import (
    CategoryInUseError,
    DuplicateCategoryNameError,
    ModCategoryView,
)
from stadtfest.application.moderation.image_ports import (
    PresignedUpload,
    ProcessedImage,
    StorageUnavailableError,
    UnsupportedImageError,
    UploadRecord,
)
from stadtfest.application.moderation.ports import (
    ModEventSummary,
    VersionConflictError,
)
from stadtfest.application.outbox.ports import OutboxMessage
from stadtfest.application.shared.ports import JsonValue
from stadtfest.domain.ai_ingestion.finds import FoundEvent
from stadtfest.domain.ai_ingestion.job import AiSearchEventType, AiSearchJob, AiSearchStatus
from stadtfest.domain.events.category import CATEGORY_CHANGED, CategoryDraft
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.events.images import (
    EventImage,
    ImageEventType,
    ImageFormat,
    ImageStatus,
    Variant,
)
from stadtfest.domain.events.maintenance import DomainEvent, ManagedEvent
from stadtfest.domain.identity.principal import Principal


@dataclass
class FixedClock:
    day: date

    def today(self) -> date:
        return self.day


@dataclass
class FakeCache:
    store: dict[str, str] = field(default_factory=dict)
    generations: dict[str, int] = field(default_factory=dict)
    ttls: dict[str, int] = field(default_factory=dict)

    async def get_json(self, key: str) -> JsonValue | None:
        raw = self.store.get(key)
        return json.loads(raw) if raw is not None else None

    async def set_json(self, key: str, value: JsonValue, ttl_seconds: int) -> None:
        self.store[key] = json.dumps(value)
        self.ttls[key] = ttl_seconds

    async def generation(self, namespace: str) -> int:
        return self.generations.get(namespace, 0)

    async def bump_generation(self, namespace: str) -> int:
        self.generations[namespace] = self.generations.get(namespace, 0) + 1
        return self.generations[namespace]


@dataclass
class FakeEventCatalog:
    """Returns canned rows; records the criteria it was called with."""

    rows: list[EventSummaryView] = field(default_factory=list)
    details: dict[UUID, EventDetailView] = field(default_factory=dict)
    counts: EventCountView = field(default_factory=lambda: EventCountView(0, {}))
    search_calls: list[tuple[SearchCriteria, PageCursor | None, int]] = field(default_factory=list)
    count_calls: int = 0

    async def search(
        self, criteria: SearchCriteria, after: PageCursor | None, limit: int
    ) -> list[EventSummaryView]:
        self.search_calls.append((criteria, after, limit))
        return copy.copy(self.rows[:limit])

    async def count(self, criteria: SearchCriteria) -> EventCountView:
        self.count_calls += 1
        return self.counts

    async def get_public(
        self, event_id: UUID, reference: GeoPoint | None
    ) -> EventDetailView | None:
        return self.details.get(event_id)


@dataclass
class FakeCategoryCatalog:
    categories: list[CategoryView] = field(default_factory=list)
    calls: int = 0

    async def list_active(self) -> list[CategoryView]:
        self.calls += 1
        return list(self.categories)


@dataclass
class FakeGeocoding:
    places: list[Place] = field(default_factory=list)
    reverse_result: Place | None = None
    unavailable: bool = False
    # Answers per query; if set, other queries find nothing.
    by_query: dict[str, list[Place]] | None = None
    search_calls: list[str] = field(default_factory=list)
    reverse_calls: list[GeoPoint] = field(default_factory=list)

    async def search(self, query: str, limit: int) -> list[Place]:
        self.search_calls.append(query)
        if self.unavailable:
            raise GeocodingUnavailableError
        if self.by_query is not None:
            return self.by_query.get(query, [])[:limit]
        return self.places[:limit]

    async def reverse(self, location: GeoPoint) -> Place | None:
        self.reverse_calls.append(location)
        if self.unavailable:
            raise GeocodingUnavailableError
        return self.reverse_result


@dataclass
class FakeUserRepository:
    users: dict[str, UserRecord] = field(default_factory=dict)
    deleted: list[str] = field(default_factory=list)

    async def get_or_create(self, subject: str, first_name: str, last_name: str) -> UserRecord:
        if subject not in self.users:
            self.users[subject] = UserRecord(uuid4(), first_name, last_name)
        return self.users[subject]

    async def update_name(self, subject: str, first_name: str, last_name: str) -> UserRecord | None:
        existing = self.users.get(subject)
        if existing is None:
            return None
        self.users[subject] = UserRecord(existing.id, first_name, last_name)
        return self.users[subject]

    async def delete_personal_data(self, subject: str) -> bool:
        self.deleted.append(subject)
        return self.users.pop(subject, None) is not None


@dataclass
class FakeIdpAdmin:
    unavailable: bool = False
    deleted: list[str] = field(default_factory=list)

    async def delete_user(self, subject: str) -> None:
        if self.unavailable:
            raise IdpUnavailableError
        self.deleted.append(subject)


@dataclass
class FakeAccountJobs:
    unavailable: bool = False
    enqueued: list[str] = field(default_factory=list)

    async def enqueue_idp_deletion(self, subject: str) -> None:
        if self.unavailable:
            raise JobQueueUnavailableError
        self.enqueued.append(subject)


@dataclass
class FakeTokenVerifier:
    """Maps opaque test tokens to claims; unknown tokens are invalid."""

    tokens: dict[str, dict[str, object]] = field(default_factory=dict)
    unavailable: bool = False

    async def verify(self, token: str) -> Claims:
        if self.unavailable:
            raise IdpUnavailableError
        if token not in self.tokens:
            raise InvalidTokenError
        return self.tokens[token]


@dataclass
class FakeDeletedAccounts:
    unavailable: bool = False
    marked: dict[str, int] = field(default_factory=dict)

    async def mark_deleted(self, subject: str, ttl_seconds: int) -> None:
        if self.unavailable:
            raise DeletedAccountsUnavailableError
        self.marked[subject] = ttl_seconds

    async def is_deleted(self, subject: str) -> bool:
        if self.unavailable:
            raise DeletedAccountsUnavailableError
        return subject in self.marked


@dataclass
class FakeFavoriteRepository:
    """Favorites per subject; only events in `public` can be added."""

    public: dict[UUID, EventSummaryView] = field(default_factory=dict)
    favorites: dict[str, list[UUID]] = field(default_factory=dict)
    counts: dict[UUID, int] = field(default_factory=dict)

    async def add(self, subject: str, event_id: UUID) -> bool:
        if event_id not in self.public:
            return False
        mine = self.favorites.setdefault(subject, [])
        if event_id not in mine:
            mine.append(event_id)
            self.counts[event_id] = self.counts.get(event_id, 0) + 1
        return True

    async def remove(self, subject: str, event_id: UUID) -> None:
        mine = self.favorites.get(subject, [])
        if event_id in mine:
            mine.remove(event_id)
            self.counts[event_id] -= 1

    async def list_for(self, subject: str, *, from_day: date | None) -> list[FavoriteView]:
        events = [self.public[event_id] for event_id in self.favorites.get(subject, [])]
        if from_day is not None:
            events = [event for event in events if event.end_date >= from_day]
        return [
            FavoriteView(event, "Stadtfest", "🎪", datetime(2026, 9, 1, tzinfo=UTC))
            for event in sorted(events, key=lambda event: event.start_date)
        ]

    async def is_favorite(self, subject: str, event_id: UUID) -> bool:
        return event_id in self.favorites.get(subject, [])


@dataclass
class FakeAccountResolver:
    """Records for whom an account was ensured; the same subject always gets the same ID."""

    ensured: list[str] = field(default_factory=list)

    async def __call__(self, principal: Principal) -> UUID:
        self.ensured.append(principal.subject)
        return uuid5(NAMESPACE_URL, principal.subject)


@dataclass
class FakeManagedEventRepository:
    """Events in memory; `save` checks the version like the database does."""

    events: dict[UUID, ManagedEvent] = field(default_factory=dict)
    outbox: list[DomainEvent] = field(default_factory=list)
    audit: list[UUID] = field(default_factory=list)
    # Shared with `FakeImageRepository(images=...)` in image tests.
    images: list[EventImage] = field(default_factory=list)

    async def list_images(self, event_id: UUID) -> list[EventImage]:
        return sorted(
            (image for image in self.images if image.event_id == event_id),
            key=lambda image: image.position,
        )

    async def list_events(self, ids: frozenset[UUID] | None) -> list[ModEventSummary]:
        return [
            ModEventSummary(
                id=e.id,
                name=e.content.name,
                status=e.status,
                start_date=e.content.start_date,
                end_date=e.content.end_date,
                place=e.content.place,
                city=e.content.city,
                category_id=e.content.category_id,
                favorite_count=e.favorite_count,
                source=e.source,
                version=e.version,
            )
            for e in self.events.values()
            if not e.deleted and (ids is None or e.id in ids)
        ]

    async def get(self, event_id: UUID) -> ManagedEvent | None:
        event = self.events.get(event_id)
        return None if event is None or event.deleted else copy.deepcopy(event)

    async def add(self, event: ManagedEvent, user_id: UUID) -> None:
        self.audit.append(user_id)
        self.outbox.extend(event.pending_events)
        event.pending_events.clear()
        event.version = 1
        self.events[event.id] = copy.deepcopy(event)

    async def save(self, event: ManagedEvent, expected_version: int, user_id: UUID) -> int:
        stored = self.events.get(event.id)
        if stored is None or stored.deleted or stored.version != expected_version:
            raise VersionConflictError
        self.audit.append(user_id)
        self.outbox.extend(event.pending_events)
        event.pending_events.clear()
        saved = copy.deepcopy(event)
        saved.version = expected_version + 1
        self.events[event.id] = saved
        return saved.version


@dataclass
class FakeActiveCategories:
    ids: frozenset[UUID] = frozenset()

    async def active_ids(self) -> frozenset[UUID]:
        return self.ids


@dataclass
class FakeOutboxStore:
    pending: list[OutboxMessage] = field(default_factory=list)
    dispatched: list[OutboxMessage] = field(default_factory=list)
    purged_before: list[datetime] = field(default_factory=list)

    async def dispatch_pending(
        self, limit: int, send: Callable[[OutboxMessage], Awaitable[None]]
    ) -> int:
        batch, self.pending = self.pending[:limit], self.pending[limit:]
        for message in batch:
            await send(message)
        self.dispatched.extend(batch)
        return len(batch)

    async def purge_dispatched(self, before: datetime) -> int:
        self.purged_before.append(before)
        return 0


@dataclass
class FakeEventQueue:
    sent: list[OutboxMessage] = field(default_factory=list)

    async def enqueue_domain_event(self, message: OutboxMessage) -> None:
        self.sent.append(message)


@dataclass
class FakeEventFavorites:
    removed: list[UUID] = field(default_factory=list)

    async def remove_for_event(self, event_id: UUID) -> int:
        self.removed.append(event_id)
        return 1


# --- images (R08) -------------------------------------------------------------------------


@dataclass
class FakeImageRepository:
    """Uploads and images in memory; records the outbox messages it would write."""

    images: list[EventImage] = field(default_factory=list)
    uploads: dict[UUID, UploadRecord] = field(default_factory=dict)
    outbox: list[tuple[str, dict[str, str | None]]] = field(default_factory=list)
    deleted_event_ids: set[UUID] = field(default_factory=set)

    def _replace(self, image_id: UUID, **changes: object) -> None:
        for index, image in enumerate(self.images):
            if image.id == image_id:
                self.images[index] = dataclasses.replace(image, **changes)  # type: ignore[arg-type]

    def _renumber(self, event_id: UUID, ordered: Sequence[UUID]) -> None:
        for position, image_id in enumerate(ordered):
            self._replace(image_id, position=position)

    async def add_upload(self, upload: UploadRecord) -> None:
        self.uploads[upload.id] = upload

    async def get_upload(self, upload_id: UUID) -> UploadRecord | None:
        return self.uploads.get(upload_id)

    async def list_for_event(self, event_id: UUID) -> list[EventImage]:
        return sorted(
            (image for image in self.images if image.event_id == event_id),
            key=lambda image: image.position,
        )

    async def get(self, image_id: UUID) -> EventImage | None:
        return next((image for image in self.images if image.id == image_id), None)

    async def attach(self, image: EventImage, consumed_at: datetime) -> None:
        current = [i.id for i in await self.list_for_event(image.event_id)]
        current.insert(image.position, image.id)
        self.images.append(image)
        self._renumber(image.event_id, current)
        if image.upload_id is not None:
            upload = self.uploads[image.upload_id]
            self.uploads[upload.id] = dataclasses.replace(upload, consumed_at=consumed_at)
        self.outbox.append(
            (
                ImageEventType.UPLOADED.value,
                {"imageId": str(image.id), "eventId": str(image.event_id)},
            )
        )

    async def reorder(self, event_id: UUID, image_ids: Sequence[UUID]) -> None:
        self._renumber(event_id, image_ids)

    async def remove(self, event_id: UUID, image_id: UUID) -> EventImage | None:
        image = await self.get(image_id)
        if image is None or image.event_id != event_id:
            return None
        self.images.remove(image)
        self._renumber(event_id, [i.id for i in await self.list_for_event(event_id)])
        self.outbox.append(
            (
                ImageEventType.REMOVED.value,
                {
                    "imageId": str(image.id),
                    "uploadId": str(image.upload_id) if image.upload_id else None,
                },
            )
        )
        return image

    async def retry(self, image_id: UUID) -> None:
        self._replace(image_id, status=ImageStatus.PROCESSING)
        self.outbox.append((ImageEventType.UPLOADED.value, {"imageId": str(image_id)}))

    async def mark_ready(self, image_id: UUID, width: int, height: int) -> bool:
        image = await self.get(image_id)
        if image is None:
            return False
        if image.upload_id is not None:
            self.uploads.pop(image.upload_id, None)
        self._replace(
            image_id, status=ImageStatus.READY, width=width, height=height, upload_id=None
        )
        return True

    async def mark_failed(self, image_id: UUID) -> None:
        self._replace(image_id, status=ImageStatus.FAILED)

    async def stale_uploads(self, created_before: datetime) -> list[UploadRecord]:
        return [
            u
            for u in self.uploads.values()
            if u.consumed_at is None and u.created_at < created_before
        ]

    async def delete_uploads(self, upload_ids: Sequence[UUID]) -> None:
        for upload_id in upload_ids:
            self.uploads.pop(upload_id, None)

    async def images_of_deleted_events(self) -> list[EventImage]:
        return [i for i in self.images if i.event_id in self.deleted_event_ids]

    async def delete_images(self, image_ids: Sequence[UUID]) -> None:
        self.images[:] = [i for i in self.images if i.id not in set(image_ids)]


@dataclass
class FakeObjectStorage:
    """Objects in memory. `uploaded` simulates files the app put via a signed URL."""

    objects: dict[str, bytes] = field(default_factory=dict)
    content_types: dict[str, str] = field(default_factory=dict)
    unavailable: bool = False
    signed: list[tuple[str, str, int]] = field(default_factory=list)

    def _check(self) -> None:
        if self.unavailable:
            raise StorageUnavailableError

    async def presign_put(
        self, key: str, content_type: str, expires_in_seconds: int
    ) -> PresignedUpload:
        self._check()
        self.signed.append((key, content_type, expires_in_seconds))
        return PresignedUpload(
            f"https://s3.test/bucket/{key}?signature=x", {"Content-Type": content_type}
        )

    async def read(self, key: str) -> bytes | None:
        self._check()
        return self.objects.get(key)

    async def size(self, key: str) -> int | None:
        self._check()
        content = self.objects.get(key)
        return None if content is None else len(content)

    async def write(self, key: str, data: bytes, content_type: str) -> None:
        self._check()
        self.objects[key] = data
        self.content_types[key] = content_type

    async def delete(self, keys: Sequence[str]) -> None:
        self._check()
        for key in keys:
            self.objects.pop(key, None)


@dataclass
class FakeImageProcessor:
    """Accepts any content starting with `IMG`; produces one tiny file per variant."""

    async def process(self, data: bytes) -> ProcessedImage:
        if not data.startswith(b"IMG"):
            raise UnsupportedImageError
        files: Mapping[tuple[Variant, ImageFormat], bytes] = {
            (variant, image_format): f"{variant}.{image_format}".encode()
            for variant in Variant
            for image_format in ImageFormat
        }
        return ProcessedImage(width=1600, height=1200, files=files)


# --- categories (R09) ---------------------------------------------------------------------


@dataclass
class FakeCategoryRepository:
    """Categories in memory; `events` maps category ID to its number of events."""

    categories: list[ModCategoryView] = field(default_factory=list)
    events: dict[UUID, int] = field(default_factory=dict)
    outbox: list[str] = field(default_factory=list)

    def _view(self, category: ModCategoryView) -> ModCategoryView:
        return dataclasses.replace(category, event_count=self.events.get(category.id, 0))

    def _check_name(self, name: str, exclude: UUID | None) -> None:
        if any(c.name.lower() == name.lower() and c.id != exclude for c in self.categories):
            raise DuplicateCategoryNameError

    async def list_all(self) -> list[ModCategoryView]:
        return [self._view(c) for c in sorted(self.categories, key=lambda c: c.sort_order)]

    async def get(self, category_id: UUID) -> ModCategoryView | None:
        found = next((c for c in self.categories if c.id == category_id), None)
        return self._view(found) if found else None

    async def add(self, category_id: UUID, draft: CategoryDraft) -> ModCategoryView:
        self._check_name(draft.name, None)
        order = max((c.sort_order for c in self.categories), default=-1) + 1
        category = ModCategoryView(
            category_id, draft.name, draft.emoji, draft.color, draft.active, order, 0
        )
        self.categories.append(category)
        self.outbox.append(CATEGORY_CHANGED)
        return category

    async def update(self, category_id: UUID, draft: CategoryDraft) -> ModCategoryView | None:
        self._check_name(draft.name, category_id)
        for i, c in enumerate(self.categories):
            if c.id == category_id:
                self.categories[i] = dataclasses.replace(
                    c, name=draft.name, emoji=draft.emoji, color=draft.color, active=draft.active
                )
                self.outbox.append(CATEGORY_CHANGED)
                return self._view(self.categories[i])
        return None

    async def reorder(self, category_ids: Sequence[UUID]) -> None:
        order = {category_id: i for i, category_id in enumerate(category_ids)}
        self.categories = [dataclasses.replace(c, sort_order=order[c.id]) for c in self.categories]
        self.outbox.append(CATEGORY_CHANGED)

    async def delete(self, category_id: UUID, replacement_id: UUID | None) -> int | None:
        if not any(c.id == category_id for c in self.categories):
            return None
        moved = self.events.get(category_id, 0)
        if moved and replacement_id is None:
            raise CategoryInUseError
        if replacement_id is not None:
            self.events[replacement_id] = self.events.get(replacement_id, 0) + moved
        self.events.pop(category_id, None)
        self.categories = [c for c in self.categories if c.id != category_id]
        self.outbox.append(CATEGORY_CHANGED)
        return moved


# --- AI search (R10) ----------------------------------------------------------------------


@dataclass
class FakeWebSearch:
    """Returns fixed hits for every query; can fail."""

    hits: list[SearchHit] = field(default_factory=list)
    unavailable: bool = False
    queries: list[str] = field(default_factory=list)
    # Single queries that fail (e.g. upstream engines blocking).
    failing: set[str] = field(default_factory=set)

    async def search(self, query: str, count: int) -> list[SearchHit]:
        if self.unavailable or query in self.failing:
            raise WebSearchUnavailableError
        self.queries.append(query)
        return self.hits[:count]


@dataclass
class FakeEventFinder:
    """Calls the search tool once per query, then returns the configured finds."""

    finds: list[FoundEvent] = field(default_factory=list)
    invalid: int = 0
    queries: list[str] = field(default_factory=lambda: ["Feste 73430"])
    unavailable: bool = False
    delay_seconds: float = 0.0
    prompts: list[tuple[str, str]] = field(default_factory=list)
    # Pages to read after searching, and what the tool answered.
    reads: list[str] = field(default_factory=list)
    read_results: list[str] = field(default_factory=list)

    async def find(
        self,
        system: str,
        prompt: str,
        search: SearchTool,
        limits: FinderLimits,
        read: PageTool | None = None,
    ) -> FinderResult:
        self.prompts.append((system, prompt))
        if self.unavailable:
            raise LlmUnavailableError
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        for query in self.queries:
            await search(query)
        if read is not None:
            for url in self.reads:
                self.read_results.append(await read(url))
        return FinderResult(list(self.finds), self.invalid, input_tokens=100, output_tokens=50)


@dataclass
class FakePageReader:
    """Page texts by URL; unknown URLs cannot be read."""

    texts: dict[str, str] = field(default_factory=dict)
    calls: list[tuple[str, int]] = field(default_factory=list)

    async def read(self, url: str, max_chars: int) -> str | None:
        self.calls.append((url, max_chars))
        return self.texts.get(url)


@dataclass
class FakeSourceChecker:
    dead: set[str] = field(default_factory=set)

    async def reachable(self, url: str) -> bool:
        return url not in self.dead


@dataclass
class FakeAiSearchRepository:
    jobs: dict[UUID, AiSearchJob] = field(default_factory=dict)
    outbox: list[str] = field(default_factory=list)

    async def add(self, job: AiSearchJob) -> None:
        self.jobs[job.id] = copy.deepcopy(job)
        self.outbox.append(AiSearchEventType.REQUESTED.value)

    async def get(self, job_id: UUID) -> AiSearchJob | None:
        job = self.jobs.get(job_id)
        return copy.deepcopy(job) if job else None

    async def list_for_moderator(
        self, moderator_id: UUID, *, active_only: bool, limit: int
    ) -> list[AiSearchJob]:
        jobs = [
            j
            for j in self.jobs.values()
            if j.moderator_id == moderator_id and (j.active or not active_only)
        ]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)[:limit]

    async def count_created_since(self, moderator_id: UUID, since: datetime) -> int:
        return sum(
            1
            for j in self.jobs.values()
            if j.moderator_id == moderator_id and j.created_at >= since
        )

    async def save(self, job: AiSearchJob) -> None:
        self.jobs[job.id] = copy.deepcopy(job)
        if job.status is AiSearchStatus.COMPLETED:
            self.outbox.append(AiSearchEventType.COMPLETED.value)
        elif job.status is AiSearchStatus.FAILED:
            self.outbox.append(AiSearchEventType.FAILED.value)

    async def stuck(self, started_before: datetime) -> list[AiSearchJob]:
        return [
            copy.deepcopy(j)
            for j in self.jobs.values()
            if j.active and j.created_at < started_before
        ]

    async def compact_logs(self, finished_before: datetime) -> int:
        changed = 0
        for job in self.jobs.values():
            if job.finished_at and job.finished_at < finished_before and job.log:
                job.log = {}
                changed += 1
        return changed


@dataclass
class FakeDraftStore:
    """Known events as (name, normalized URL); rejected URLs; stored drafts."""

    known_names: set[str] = field(default_factory=set)
    known_urls: set[str] = field(default_factory=set)
    stored: list[DraftCandidate] = field(default_factory=list)

    async def is_duplicate(self, candidate: DraftCandidate, normalized_url: str) -> bool:
        return candidate.find.name in self.known_names or normalized_url in self.known_urls

    async def add_drafts(
        self, job_id: UUID, found_at: datetime, drafts: Sequence[DraftCandidate]
    ) -> list[UUID]:
        self.stored.extend(drafts)
        return [uuid4() for _ in drafts]
