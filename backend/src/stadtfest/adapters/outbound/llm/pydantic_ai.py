"""The one generic LLM adapter, built on Pydantic AI (ADR 0012).

The provider is chosen by settings only (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`,
`LLM_BASE_URL`). The web search tool and the output schema `EventDraftV1` are passed in a
provider-independent way. The model output is parsed leniently; every find is then
validated on its own, so one broken find does not discard the others.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import httpx
from pydantic import BaseModel, Field, ValidationError
from pydantic_ai import (
    Agent,
    AgentRunError,
    ModelAPIError,
    RunContext,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UsageLimits,
)
from pydantic_ai.models import Model

from stadtfest.application.ai_ingestion.ports import (
    FinderLimits,
    FinderResult,
    LlmUnavailableError,
    SearchTool,
)
from stadtfest.domain.ai_ingestion.finds import FoundEvent


class LlmKind(StrEnum):
    """Supported providers (the fake lives in `fake.py`)."""

    MISTRAL = "mistral"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


@dataclass(frozen=True, slots=True)
class LlmConfig:
    """Provider settings; switching provider changes only these values."""

    kind: LlmKind
    model: str
    api_key: str | None = None
    base_url: str | None = None


def build_model(config: LlmConfig) -> Model:
    """Create the Pydantic AI model for the configured provider."""
    if config.kind is LlmKind.MISTRAL:
        from pydantic_ai.models.mistral import MistralModel
        from pydantic_ai.providers.mistral import MistralProvider

        return MistralModel(
            config.model,
            provider=MistralProvider(api_key=config.api_key, base_url=config.base_url),
        )
    if config.kind is LlmKind.OPENAI:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(
            config.model,
            provider=OpenAIProvider(api_key=config.api_key, base_url=config.base_url),
        )
    if config.kind is LlmKind.ANTHROPIC:
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(
            config.model,
            provider=AnthropicProvider(api_key=config.api_key, base_url=config.base_url),
        )
    if config.kind is LlmKind.GOOGLE:
        # Gemini API (Google AI Studio); ADR 0014.
        from google.genai.types import HttpRetryOptions
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        return GoogleModel(
            config.model,
            provider=GoogleProvider(
                api_key=config.api_key,
                base_url=config.base_url,
                # Unlike the OpenAI and Anthropic SDKs, google-genai does not retry by
                # default; the free tier often answers 503 "high demand" (seen 05.10.2026).
                # Up to 5 attempts, about 30 s of waiting, well inside AI_SEARCH_TIMEOUT_S.
                retry_options=HttpRetryOptions(attempts=5, initial_delay=2.0, max_delay=16.0),
            ),
        )
    from pydantic_ai.models.ollama import OllamaModel
    from pydantic_ai.providers.ollama import OllamaProvider

    return OllamaModel(
        config.model,
        provider=OllamaProvider(base_url=config.base_url or "http://localhost:11434/v1"),
    )


class Coordinates(BaseModel):
    """WGS84 position."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class EventDraftV1(BaseModel):
    """Fixed, versioned output schema of one find (CLAUDE.md "AI ingestion")."""

    name: str = Field(min_length=1, max_length=120, description="Name der Veranstaltung")
    date_from: date = Field(description="Erster Tag, JJJJ-MM-TT")
    date_to: date = Field(description="Letzter Tag, JJJJ-MM-TT")
    place: str = Field(default="", max_length=120, description="Ort, z. B. Marktplatz")
    address: str = Field(default="", max_length=200, description="Straße, PLZ Ort")
    coordinates: Coordinates | None = Field(default=None, description="Falls bekannt")
    category: str | None = Field(default=None, max_length=60, description="Art des Festes")
    source_url: str = Field(min_length=8, max_length=500, description="Seite aus der Suche")
    description: str | None = Field(default=None, max_length=1000)


class _LooseDraft(BaseModel):
    """`EventDraftV1` as the model sees it, every field optional.

    One broken find thus never breaks the whole answer; each item is then validated
    strictly with `EventDraftV1`.
    """

    name: str | None = Field(default=None, description="Name der Veranstaltung")
    date_from: str | None = Field(default=None, description="Erster Tag, JJJJ-MM-TT")
    date_to: str | None = Field(default=None, description="Letzter Tag, JJJJ-MM-TT")
    place: str | None = Field(default=None, description="Ort, z. B. Marktplatz")
    address: str | None = Field(default=None, description="Straße, PLZ Ort")
    coordinates: dict[str, float] | None = Field(
        default=None, description="Falls bekannt: {lat, lon}"
    )
    category: str | None = Field(default=None, description="Art des Festes")
    source_url: str | None = Field(default=None, description="Seite aus der Websuche")
    description: str | None = Field(default=None, description="Kurze Beschreibung")


class _Finds(BaseModel):
    """What the model returns."""

    events: list[_LooseDraft] = Field(default_factory=list)


def _to_find(loose: _LooseDraft) -> FoundEvent | None:
    try:
        draft = EventDraftV1.model_validate(loose.model_dump(exclude_none=True))
    except ValidationError:
        return None
    return FoundEvent(
        name=draft.name.strip(),
        date_from=draft.date_from,
        date_to=draft.date_to,
        place=draft.place.strip(),
        address=draft.address.strip(),
        source_url=draft.source_url.strip(),
        lat=draft.coordinates.lat if draft.coordinates else None,
        lon=draft.coordinates.lon if draft.coordinates else None,
        category=draft.category,
        description=draft.description,
    )


class PydanticAiEventFinder:
    """Implements `EventFinder` for Mistral, OpenAI, Anthropic and Ollama alike."""

    def __init__(self, model: Model) -> None:
        """Create the adapter for an already configured model (see `build_model`)."""
        self._agent: Agent[SearchTool, _Finds] = Agent(
            model, output_type=_Finds, deps_type=SearchTool, retries=1
        )

        @self._agent.tool
        async def web_search(ctx: RunContext[SearchTool], query: str) -> list[dict[str, str]]:
            """Websuche (Deutschland). Liefert Titel, URL und Kurztext der Treffer."""
            hits = await ctx.deps(query)
            return [{"title": h.title, "url": h.url, "snippet": h.snippet} for h in hits]

    async def find(
        self, system: str, prompt: str, search: SearchTool, limits: FinderLimits
    ) -> FinderResult:
        """Run the agent with the search tool and validate each find."""
        try:
            result = await self._agent.run(
                prompt,
                deps=search,
                instructions=system,
                usage_limits=UsageLimits(
                    tool_calls_limit=limits.max_tool_calls + 1,
                    output_tokens_limit=limits.max_output_tokens,
                    request_limit=limits.max_tool_calls + 4,
                ),
            )
        except (
            UsageLimitExceeded,
            ModelAPIError,
            UnexpectedModelBehavior,
            AgentRunError,
            httpx.HTTPError,
        ) as exc:
            raise LlmUnavailableError from exc
        finds: list[FoundEvent] = []
        invalid = 0
        for raw in result.output.events:
            find = _to_find(raw)
            if find is None:
                invalid += 1
            else:
                finds.append(find)
        usage = result.usage
        return FinderResult(
            finds=finds,
            invalid=invalid,
            input_tokens=usage.input_tokens or 0,
            output_tokens=usage.output_tokens or 0,
        )
