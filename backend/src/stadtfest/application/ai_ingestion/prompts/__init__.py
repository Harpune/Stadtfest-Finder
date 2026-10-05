"""Bundled prompt versions of the AI search (`AI_SEARCH_PROMPT_VERSION`).

Each version is a Markdown file in this package; see `parse_prompt` for the format.
"""

from __future__ import annotations

from importlib import resources

from stadtfest.domain.ai_ingestion.prompt import InvalidPromptError, PromptTemplate, parse_prompt

DEFAULT_VERSION = "v3"


def bundled_versions() -> tuple[str, ...]:
    """Names of the bundled versions, e.g. `("v1", "v2")`."""
    files = resources.files(__package__).iterdir()
    return tuple(sorted(f.name.removesuffix(".md") for f in files if f.name.endswith(".md")))


def load_bundled(version: str) -> PromptTemplate:
    """The bundled prompt of this version.

    Raises:
        InvalidPromptError: Unknown version or invalid template.
    """
    if version not in bundled_versions():
        raise InvalidPromptError(f"unknown prompt version {version!r}")
    text = resources.files(__package__).joinpath(f"{version}.md").read_text(encoding="utf-8")
    return parse_prompt(version, text)
