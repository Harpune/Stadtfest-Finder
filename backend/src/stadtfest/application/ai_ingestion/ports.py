"""Outbound ports of the AI search (R10): LLM, web search, source check, persistence."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from stadtfest.domain.ai_ingestion.finds import FoundEvent
from stadtfest.domain.ai_ingestion.job import AiSearchJob
from stadtfest.domain.events.geo import GeoPoint


class LlmUnavailableError(Exception):
    """The LLM provider cannot be reached, rejected the request or broke a limit."""


class WebSearchUnavailableError(Exception):
    """The web search provider cannot be reached or rejected the request."""


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One web search result."""

    url: str
    title: str
    snippet: str = ""


class WebSearchPort(Protocol):
    """Web search used as tool of the LLM (provider chosen by ADR, switchable via env)."""

    async def search(self, query: str, count: int) -> list[SearchHit]:
        """Search the web (German results).

        Raises:
            WebSearchUnavailableError: If the provider fails.
        """
        ...


# The tool the LLM calls; the application wraps the web search to record queries and URLs.
SearchTool = Callable[[str], Awaitable[list[SearchHit]]]


@dataclass(frozen=True, slots=True)
class FinderLimits:
    """Upper bounds of one LLM run."""

    max_tool_calls: int
    max_output_tokens: int = 8000


@dataclass(frozen=True, slots=True)
class FinderResult:
    """Structurally valid finds, the number of invalid ones, and token usage."""

    finds: list[FoundEvent]
    invalid: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class EventFinder(Protocol):
    """LLM port: one generic adapter for all providers (CLAUDE.md "AI ingestion")."""

    async def find(
        self, system: str, prompt: str, search: SearchTool, limits: FinderLimits
    ) -> FinderResult:
        """Let the LLM search with the tool and return finds in the fixed schema.

        Each find is validated on its own: invalid ones are only counted.

        Raises:
            LlmUnavailableError: Provider failure or limit exceeded.
            WebSearchUnavailableError: Raised by the tool and passed through.
        """
        ...


class SourceChecker(Protocol):
    """Checks that a source page answers (HEAD/GET, status < 400, timeout 5 s)."""

    async def reachable(self, url: str) -> bool:
        """True if the page answers without error."""
        ...


@dataclass(frozen=True, slots=True)
class DraftCandidate:
    """A checked find ready to be stored as draft."""

    find: FoundEvent
    location: GeoPoint
    postal_code: str
    city: str
    category_id: UUID | None


class AiSearchRepository(Protocol):
    """Jobs in `ai_search_job`; changes write `ai_search.*` to the outbox (one transaction)."""

    async def add(self, job: AiSearchJob) -> None:
        """Store a queued job and write `ai_search.requested`."""
        ...

    async def get(self, job_id: UUID) -> AiSearchJob | None:
        """One job, or None."""
        ...

    async def list_for_moderator(
        self, moderator_id: UUID, *, active_only: bool, limit: int
    ) -> list[AiSearchJob]:
        """The moderator's jobs, newest first."""
        ...

    async def count_created_since(self, moderator_id: UUID, since: datetime) -> int:
        """Jobs the moderator started since the given time (daily limit)."""
        ...

    async def save(self, job: AiSearchJob) -> None:
        """Store status, result and log; writes `ai_search.completed|failed` when finished."""
        ...

    async def stuck(self, started_before: datetime) -> list[AiSearchJob]:
        """Queued or running jobs created before the given time (worker crash)."""
        ...

    async def compact_logs(self, finished_before: datetime) -> int:
        """Reduce logs of old jobs to their counters; returns the number changed."""
        ...


class DraftStore(Protocol):
    """Events for duplicate checks and new drafts (moderation context)."""

    async def is_duplicate(self, candidate: DraftCandidate, normalized_url: str) -> bool:
        """True if the find already exists or its source was rejected (nationwide).

        An event (not deleted) matches with a similar name (trgm >= 0.5), overlapping dates
        and a distance below 2 km, or with the same source.
        """
        ...

    async def add_drafts(
        self, job_id: UUID, found_at: datetime, drafts: Sequence[DraftCandidate]
    ) -> list[UUID]:
        """Store the candidates as drafts (`source = ai`); returns their IDs."""
        ...


@dataclass(frozen=True, slots=True)
class SearchLog:
    """What a job did; never user data (R10-US3, 90 days)."""

    queries: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
