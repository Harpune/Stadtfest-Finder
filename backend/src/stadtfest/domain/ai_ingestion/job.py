"""AI search job: status machine and result counters (R10-US2/US3)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AiSearchStatus(StrEnum):
    """`queued → running → completed | failed`."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AiSearchError(StrEnum):
    """Why a job failed (shown in the app as "Suche fehlgeschlagen")."""

    LLM_UNAVAILABLE = "llm_unavailable"
    SEARCH_UNAVAILABLE = "search_unavailable"
    TIMEOUT = "timeout"
    INTERNAL = "internal"


class AiSearchEventType(StrEnum):
    """Domain events of AI searches (outbox, ADR 0005)."""

    REQUESTED = "ai_search.requested"
    COMPLETED = "ai_search.completed"
    FAILED = "ai_search.failed"


ACTIVE_STATUSES = frozenset({AiSearchStatus.QUEUED, AiSearchStatus.RUNNING})


@dataclass(frozen=True, slots=True)
class SkipCounts:
    """Finds that were not stored, by reason. Counts only, never content."""

    duplicate: int = 0
    out_of_region: int = 0
    invalid: int = 0
    unverified_source: int = 0

    def add(self, reason: SkipReason) -> SkipCounts:
        """One more skipped find for the reason."""
        name = reason.value
        return replace(self, **{name: getattr(self, name) + 1})


class SkipReason(StrEnum):
    """Why a find was not stored as draft (R10-US3 steps 5-9)."""

    DUPLICATE = "duplicate"
    OUT_OF_REGION = "out_of_region"
    INVALID = "invalid"
    UNVERIFIED_SOURCE = "unverified_source"


class InvalidJobTransitionError(Exception):
    """The job is not in the status the transition starts from."""


@dataclass(slots=True)
class AiSearchJob:
    """One AI search of a moderator for a postal code of their region."""

    id: UUID
    moderator_id: UUID | None
    region_id: UUID
    postal_code: str
    place_name: str
    created_at: datetime
    status: AiSearchStatus = AiSearchStatus.QUEUED
    started_at: datetime | None = None
    finished_at: datetime | None = None
    new_event_ids: tuple[UUID, ...] = ()
    skipped: SkipCounts = field(default_factory=SkipCounts)
    error_code: AiSearchError | None = None
    log: dict[str, object] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        """Queued or running."""
        return self.status in ACTIVE_STATUSES

    def start(self, now: datetime) -> None:
        """Queued → running.

        Raises:
            InvalidJobTransitionError: If the job is not queued (e.g. delivered twice).
        """
        if self.status is not AiSearchStatus.QUEUED:
            raise InvalidJobTransitionError
        self.status = AiSearchStatus.RUNNING
        self.started_at = now

    def complete(
        self,
        new_event_ids: tuple[UUID, ...],
        skipped: SkipCounts,
        log: dict[str, object],
        now: datetime,
    ) -> None:
        """Running → completed with the stored drafts and counters."""
        if self.status is not AiSearchStatus.RUNNING:
            raise InvalidJobTransitionError
        self.status = AiSearchStatus.COMPLETED
        self.new_event_ids = new_event_ids
        self.skipped = skipped
        self.log = log
        self.finished_at = now

    def fail(self, error: AiSearchError, log: dict[str, object], now: datetime) -> None:
        """Queued or running → failed."""
        if not self.active:
            raise InvalidJobTransitionError
        self.status = AiSearchStatus.FAILED
        self.error_code = error
        self.log = log
        self.finished_at = now
