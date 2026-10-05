"""Compare prompt versions of the AI search with the configured providers (`make ai-eval`).

Runs the real pipeline (LLM, web search, geocoding, source check, duplicate check) for some
postal codes and prints a Markdown report, but stores nothing: jobs stay in memory and
drafts are only collected. Never part of CI; every run costs provider requests.

    python -m stadtfest.bootstrap.ai_eval 73430 89073 --prompts v1,v2 --out report.md
"""

from __future__ import annotations

import argparse
import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from stadtfest.adapters.outbound.persistence.ai_search import SqlDraftStore
from stadtfest.application.ai_ingestion.ports import DraftCandidate
from stadtfest.application.ai_ingestion.prompts import load_bundled
from stadtfest.application.ai_ingestion.use_cases import RunAiSearch
from stadtfest.bootstrap.container import AiSearchParts, Container
from stadtfest.bootstrap.settings import ai_search_prompt, load_settings
from stadtfest.domain.ai_ingestion.job import AiSearchJob
from stadtfest.domain.ai_ingestion.prompt import PromptTemplate


class _MemoryJobs:
    """Jobs of one eval run; nothing reaches the database."""

    def __init__(self) -> None:
        self.jobs: dict[UUID, AiSearchJob] = {}

    async def add(self, job: AiSearchJob) -> None:
        self.jobs[job.id] = job

    async def get(self, job_id: UUID) -> AiSearchJob | None:
        return self.jobs.get(job_id)

    async def save(self, job: AiSearchJob) -> None:
        self.jobs[job.id] = job

    async def list_for_moderator(
        self, moderator_id: UUID, *, active_only: bool, limit: int
    ) -> list[AiSearchJob]:
        return []

    async def count_created_since(self, moderator_id: UUID, since: datetime) -> int:
        return 0

    async def stuck(self, started_before: datetime) -> list[AiSearchJob]:
        return []

    async def compact_logs(self, finished_before: datetime) -> int:
        return 0


@dataclass
class _DryDrafts:
    """Duplicate checks against the real database, but drafts are only collected."""

    sql: SqlDraftStore
    collected: list[DraftCandidate] = field(default_factory=list)

    async def is_duplicate(self, candidate: DraftCandidate, normalized_url: str) -> bool:
        return await self.sql.is_duplicate(candidate, normalized_url)

    async def add_drafts(
        self, job_id: UUID, found_at: datetime, drafts: Sequence[DraftCandidate]
    ) -> list[UUID]:
        self.collected.extend(drafts)
        return [uuid4() for _ in drafts]


@dataclass(frozen=True)
class _Run:
    postal_code: str
    prompt: str
    job: AiSearchJob | None
    drafts: list[DraftCandidate]
    seconds: float
    note: str = ""


async def _run_one(
    parts: AiSearchParts, sql: SqlDraftStore, code: str, prompt: PromptTemplate
) -> _Run:
    started = time.monotonic()
    places = await parts.geocoding.search(code, 5)
    place = next((p for p in places if p.postal_code == code), None)
    if place is None:
        return _Run(code, prompt.version, None, [], 0.0, "postal code unknown")
    jobs, drafts = _MemoryJobs(), _DryDrafts(sql)
    runner = RunAiSearch(
        jobs,
        parts.finder,
        parts.search,
        parts.sources,
        parts.geocoding,
        parts.catalog,
        drafts,
        parts.clock,
        replace(parts.settings, prompt=prompt),
    )
    job = AiSearchJob(uuid4(), None, code, place.city, datetime.now(UTC))
    await jobs.add(job)
    done = await runner(job.id)
    return _Run(code, prompt.version, done, drafts.collected, time.monotonic() - started)


def _report(runs: list[_Run]) -> str:
    lines = [
        "# KI-Suche: Vergleich der Prompt-Versionen",
        "",
        "| PLZ | Prompt | Status | Neu | Duplikat | Außerhalb | Ungültig | Ohne Quelle "
        "| Suchen | Tokens | Sekunden |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        job = run.job
        if job is None:
            lines.append(f"| {run.postal_code} | {run.prompt} | {run.note} |" + " - |" * 8)
            continue
        tokens = job.log.get("tokens") or {}
        queries = _strings(job.log.get("queries"))
        status = job.status.value + (f" ({job.error_code.value})" if job.error_code else "")
        lines.append(
            f"| {run.postal_code} | {run.prompt} | {status} | {len(run.drafts)} "
            f"| {job.skipped.duplicate} | {job.skipped.out_of_area} | {job.skipped.invalid} "
            f"| {job.skipped.unverified_source} | {len(queries)} "
            f"| {_tokens(tokens)} | {run.seconds:.0f} |"
        )
    for run in runs:
        if run.job is None:
            continue
        lines += ["", f"## {run.postal_code} {run.job.place_name} · {run.prompt}", ""]
        nearby = _strings(run.job.log.get("nearbyPlaces"))
        if nearby:
            lines.append(f"Orte im Umkreis: {', '.join(nearby)}")
            lines.append("")
        lines.append("Suchanfragen:")
        lines += [f"- {query}" for query in _strings(run.job.log.get("queries"))]
        lines += ["", "Neue Funde:"]
        lines += [
            f"- {d.find.name} · {d.find.date_from:%d.%m.%Y}-{d.find.date_to:%d.%m.%Y} · "
            f"{d.city} · {d.find.source_url}"
            for d in run.drafts
        ] or ["- keine"]
    return "\n".join(lines) + "\n"


def _tokens(tokens: object) -> str:
    if isinstance(tokens, dict):
        return f"{tokens.get('input', 0)}/{tokens.get('output', 0)}"
    return "-"


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


async def main(argv: Sequence[str] | None = None) -> None:
    """Run the comparison and print (or write) the report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("postal_codes", nargs="+", help="e.g. 73430 89073")
    parser.add_argument(
        "--prompts", default="", help="comma-separated versions, default: configured prompt"
    )
    parser.add_argument("--out", type=Path, help="write the Markdown report to this file")
    parser.add_argument(
        "--pause",
        type=float,
        default=30.0,
        help="seconds between runs, for per-minute rate limits (default 30)",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    prompts = (
        [load_bundled(v.strip()) for v in args.prompts.split(",") if v.strip()]
        if args.prompts
        else [ai_search_prompt(settings)]
    )
    container = Container.build(settings)
    try:
        sql = SqlDraftStore(container.sessions)
        runs: list[_Run] = []
        for code in args.postal_codes:
            for prompt in prompts:
                if runs:
                    await asyncio.sleep(args.pause)
                runs.append(await _run_one(container.ai_parts, sql, code, prompt))
    finally:
        await container.aclose()
    report = _report(runs)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
