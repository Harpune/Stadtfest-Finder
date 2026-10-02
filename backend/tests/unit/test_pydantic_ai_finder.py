"""The generic LLM adapter (ADR 0012) with a scripted model; never a real provider."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from stadtfest.adapters.outbound.llm.pydantic_ai import (
    LlmConfig,
    LlmKind,
    PydanticAiEventFinder,
    build_model,
)
from stadtfest.application.ai_ingestion.ports import (
    FinderLimits,
    LlmUnavailableError,
    SearchHit,
)

FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "llm" / "finds_73430.json").read_text()
)


def _scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """First turn: search; second turn: the recorded structured output."""
    searched = any(
        isinstance(part, ToolReturnPart) and part.tool_name == "web_search"
        for message in messages
        for part in getattr(message, "parts", [])
    )
    if not searched:
        return ModelResponse(parts=[ToolCallPart("web_search", {"query": "Feste 73430 Aalen"})])
    output_tool = info.output_tools[0].name
    return ModelResponse(parts=[ToolCallPart(output_tool, {"events": FIXTURE["events"]})])


async def test_finds_are_validated_one_by_one() -> None:
    queries: list[str] = []

    async def search(query: str) -> list[SearchHit]:
        queries.append(query)
        return [SearchHit("https://www.aalen.de/stadtfest", "Stadtfest Aalen")]

    finder = PydanticAiEventFinder(FunctionModel(_scripted))
    result = await finder.find("System", "Prompt", search, FinderLimits(max_tool_calls=8))

    assert queries == ["Feste 73430 Aalen"]
    assert result.invalid == 1
    assert len(result.finds) == 1
    find = result.finds[0]
    assert (find.name, find.lat, find.category) == ("Aalener Stadtfest", 48.8368, "Stadtfest")
    assert result.input_tokens > 0


async def test_model_failures_mean_unavailable() -> None:
    def broken(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart("web_search", {"query": "x"})])

    async def search(query: str) -> list[SearchHit]:
        return []

    finder = PydanticAiEventFinder(FunctionModel(broken))
    with pytest.raises(LlmUnavailableError):
        await finder.find("System", "Prompt", search, FinderLimits(max_tool_calls=2))


@pytest.mark.parametrize(
    ("kind", "model_class"),
    [
        (LlmKind.MISTRAL, "MistralModel"),
        (LlmKind.OPENAI, "OpenAIChatModel"),
        (LlmKind.ANTHROPIC, "AnthropicModel"),
        (LlmKind.OLLAMA, "OllamaModel"),
    ],
)
def test_every_provider_is_configuration_only(kind: LlmKind, model_class: str) -> None:
    """DoD: switching the provider needs only env values, no code change."""
    model = build_model(LlmConfig(kind, "some-model", api_key="test-key"))

    assert type(model).__name__ == model_class
    assert model.model_name == "some-model"
