"""The production environment contract starts with valid settings (R16-US2).

`infra/komodo-environment.example` lists every variable the backend containers get in the
HomeLab stack `stadtfest`, including the values the HomeLab compose file derives. Filled
with dummy secrets it must pass the fail-fast validation in prod and cover every setting.
"""

from __future__ import annotations

import base64
import json
import re

import pytest

from stadtfest.bootstrap.settings import Environment, Settings, load_settings
from tests.conftest import REPO_ROOT

CONTRACT = REPO_ROOT / "infra" / "komodo-environment.example"
# Settings that production deliberately leaves at their defaults or that only apply to
# other adapters (Keycloak locally) or local experiments.
NOT_IN_PRODUCTION = {
    "AUTH_JWKS_URL",  # discovered from AUTH_ISSUER
    "IDP_ADMIN_CLIENT_ID",  # keycloak only
    "IDP_ADMIN_CLIENT_SECRET",  # keycloak only
    "AI_SEARCH_PROMPT_FILE",  # rejected in prod
}
_PLACEHOLDER = re.compile(r"\[\[([A-Z0-9_]+)\]\]")
# Komodo secrets whose value must have a format; everything else gets a dummy string.
_DUMMY_SECRETS = {
    "STADTFEST_APNS_KEY_BASE64": base64.b64encode(b"-----BEGIN PRIVATE KEY-----").decode(),
    "STADTFEST_FCM_CREDENTIALS_BASE64": base64.b64encode(
        json.dumps({"client_email": "push@x.iam", "private_key": "pem"}).encode()
    ).decode(),
}


def _contract() -> dict[str, str]:
    """The contract with Komodo's `[[SECRET]]` references replaced by dummy values."""
    values: dict[str, str] = {}
    for line in CONTRACT.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = _PLACEHOLDER.sub(
            lambda m: _DUMMY_SECRETS.get(m.group(1), f"dummy-{m.group(1).lower()}"), value
        )
    return values


@pytest.fixture
def production_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.chdir(str(tmp_path))  # no .env file
    for name, value in _contract().items():
        monkeypatch.setenv(name, value)


@pytest.mark.usefixtures("production_environment")
def test_contract_passes_production_validation() -> None:
    settings = load_settings()

    assert settings.env is Environment.PROD
    assert settings.llm_provider.value in {"mistral", "ollama"}
    assert settings.push_provider.value == "direct"
    assert settings.fcm_credentials()["client_email"] == "push@x.iam"
    # One level below the domain: Cloudflare's universal certificate covers *.DOMAIN only.
    for url in (settings.mcp_public_url, settings.s3_public_base_url, settings.deep_link_base_url):
        assert url.host is not None
        assert url.host.count(".") == 2, url.host


def test_every_backend_setting_is_in_the_contract() -> None:
    missing = {name.upper() for name in Settings.model_fields} - set(_contract())

    assert missing - NOT_IN_PRODUCTION == set(), "add these to infra/komodo-environment.example"
