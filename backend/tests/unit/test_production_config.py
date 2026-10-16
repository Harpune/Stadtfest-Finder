"""The production stack configuration starts with valid settings (R16-US2).

The backend services of `infra/compose.yaml` get the Komodo stack environment
(`infra/komodo-environment.example`) as env file plus the values derived in compose
(`x-app-environment`). Together they must pass the fail-fast validation in prod.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from stadtfest.bootstrap.settings import Environment, Settings, load_settings
from tests.conftest import REPO_ROOT

INFRA = REPO_ROOT / "infra"
# Settings that production deliberately leaves at their defaults or that only apply to
# other adapters (Keycloak locally) or local experiments.
NOT_IN_PRODUCTION = {
    "AUTH_JWKS_URL",  # discovered from AUTH_ISSUER
    "IDP_ADMIN_CLIENT_ID",  # keycloak only
    "IDP_ADMIN_CLIENT_SECRET",  # keycloak only
    "AI_SEARCH_PROMPT_FILE",  # rejected in prod
}
_PLACEHOLDER = re.compile(r"\[\[([A-Z0-9_]+)\]\]")
_INTERPOLATION = re.compile(r"\$\{([A-Z0-9_]+)(?::?[-?][^}]*)?\}")


def _stack_environment() -> dict[str, str]:
    """The template with Komodo's `[[SECRET]]` references replaced by dummy values."""
    values: dict[str, str] = {}
    for line in (INFRA / "komodo-environment.example").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = _PLACEHOLDER.sub(lambda m: f"dummy-{m.group(1).lower()}", value)
    return values


def _compose_environment(stack: dict[str, str]) -> dict[str, str]:
    """`x-app-environment` of compose.yaml, interpolated like `docker compose` does."""
    compose = yaml.safe_load((INFRA / "compose.yaml").read_text())
    derived: dict[str, str] = compose["x-app-environment"]

    def interpolate(match: re.Match[str]) -> str:
        default = re.match(r":-(.*)", match.group(0)[len(match.group(1)) + 2 : -1])
        return stack.get(match.group(1)) or (default.group(1) if default else "")

    return {name: _INTERPOLATION.sub(interpolate, str(value)) for name, value in derived.items()}


@pytest.fixture
def production_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, str]:
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.chdir(tmp_path)  # no .env file
    stack = _stack_environment()
    environment = {**stack, **_compose_environment(stack)}
    # Secret files are mounted from $SECRETS_DIR/push in production.
    for name in ("APNS_KEY_PATH", "FCM_CREDENTIALS_PATH"):
        secret_file = tmp_path / Path(environment[name]).name
        secret_file.write_text("dummy")
        environment[name] = str(secret_file)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    return environment


def test_stack_environment_passes_production_validation(
    production_environment: dict[str, str],
) -> None:
    settings = load_settings()

    assert settings.env is Environment.PROD
    assert settings.llm_provider.value in {"mistral", "ollama"}
    assert settings.push_provider.value == "direct"
    assert str(settings.mcp_public_url).startswith("https://mcp.")


def test_every_backend_setting_is_configured_for_production() -> None:
    stack = _stack_environment()
    configured = set(stack) | set(_compose_environment(stack)) | {"MCP_HOST", "MCP_PORT"}

    missing = {name.upper() for name in Settings.model_fields} - configured - NOT_IN_PRODUCTION

    assert missing == set(), "add these to infra/komodo-environment.example or compose.yaml"
