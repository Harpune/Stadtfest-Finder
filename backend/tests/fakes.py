"""In-memory fake adapters for all ports (unit tests)."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

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
    IdpUnavailableError,
    InvalidTokenError,
    JobQueueUnavailableError,
    RegionRecord,
    UserRecord,
)
from stadtfest.application.shared.ports import JsonValue
from stadtfest.domain.events.geo import GeoPoint


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
    search_calls: list[str] = field(default_factory=list)
    reverse_calls: list[GeoPoint] = field(default_factory=list)

    async def search(self, query: str, limit: int) -> list[Place]:
        self.search_calls.append(query)
        if self.unavailable:
            raise GeocodingUnavailableError
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
class FakeRegionDirectory:
    regions: dict[str, RegionRecord] = field(default_factory=dict)

    async def get_by_key(self, key: str) -> RegionRecord | None:
        return self.regions.get(key)


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
