import pytest

from stadtfest.bootstrap.settings import Environment, SettingsError, load_settings


@pytest.fixture(autouse=True)
def _storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://seaweedfs:8333")
    monkeypatch.setenv("S3_PUBLIC_BASE_URL", "https://images.example.eu/stadtfest-images")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "secret")
    # Prod rejects the fake AI providers; Ollama needs no key.
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "searxng")
    monkeypatch.setenv("WEB_SEARCH_BASE_URL", "http://searxng:8080")


def test_missing_required_variables_fail_fast_with_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.chdir("/")  # no .env file

    with pytest.raises(SettingsError) as exc_info:
        load_settings()

    assert "DATABASE_URL" in str(exc_info.value)
    assert "REDIS_URL" in str(exc_info.value)


def test_invalid_value_is_named_but_never_echoed(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "not-a-url-but-a-secret-s3cr3t"
    monkeypatch.chdir("/")
    monkeypatch.setenv("DATABASE_URL", secret)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    with pytest.raises(SettingsError) as exc_info:
        load_settings()

    assert "DATABASE_URL" in str(exc_info.value)
    assert secret not in str(exc_info.value)


def test_valid_environment_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("NOMINATIM_URL", "http://nominatim:8080")
    # `make` exports the local .env (often GEOCODING_PROVIDER=fake) into the environment.
    monkeypatch.delenv("GEOCODING_PROVIDER", raising=False)
    _set_prod_auth(monkeypatch)

    settings = load_settings()

    assert settings.env is Environment.PROD
    assert settings.is_production


def test_fake_geocoding_is_rejected_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("GEOCODING_PROVIDER", "fake")

    with pytest.raises(SettingsError, match="GEOCODING_PROVIDER=fake"):
        load_settings()


def test_nominatim_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.delenv("NOMINATIM_URL", raising=False)
    monkeypatch.setenv("GEOCODING_PROVIDER", "nominatim")

    with pytest.raises(SettingsError, match="NOMINATIM_URL"):
        load_settings()


def _set_prod_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_ISSUER", "https://stadtfest.eu1.zitadel.cloud")
    monkeypatch.setenv("IDP_ADMIN_PROVIDER", "zitadel")
    monkeypatch.setenv("IDP_ADMIN_TOKEN", "pat-value")
    for name in ("IDP_ADMIN_CLIENT_ID", "IDP_ADMIN_CLIENT_SECRET", "AUTH_JWKS_URL"):
        monkeypatch.delenv(name, raising=False)


def _prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("GEOCODING_PROVIDER", "nominatim")
    monkeypatch.setenv("NOMINATIM_URL", "http://nominatim:8080")
    _set_prod_auth(monkeypatch)


def test_http_issuer_is_rejected_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    _prod(monkeypatch)
    monkeypatch.setenv("AUTH_ISSUER", "http://zitadel.local")

    with pytest.raises(SettingsError) as exc_info:
        load_settings()

    assert "AUTH_ISSUER" in str(exc_info.value)


def test_fake_idp_admin_is_rejected_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    _prod(monkeypatch)
    monkeypatch.setenv("IDP_ADMIN_PROVIDER", "fake")

    with pytest.raises(SettingsError) as exc_info:
        load_settings()

    assert "IDP_ADMIN_PROVIDER" in str(exc_info.value)


def test_idp_admin_credentials_are_required(monkeypatch: pytest.MonkeyPatch) -> None:
    _prod(monkeypatch)
    monkeypatch.delenv("IDP_ADMIN_TOKEN")

    with pytest.raises(SettingsError) as exc_info:
        load_settings()

    assert "IDP_ADMIN_TOKEN" in str(exc_info.value)
    assert "pat-value" not in str(exc_info.value)


def test_keycloak_admin_needs_client_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _prod(monkeypatch)
    monkeypatch.setenv("IDP_ADMIN_PROVIDER", "keycloak")

    with pytest.raises(SettingsError) as exc_info:
        load_settings()

    assert "IDP_ADMIN_CLIENT_SECRET" in str(exc_info.value)


def test_public_image_url_must_use_https_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("NOMINATIM_URL", "http://nominatim:8080")
    monkeypatch.delenv("GEOCODING_PROVIDER", raising=False)
    _set_prod_auth(monkeypatch)
    monkeypatch.setenv("S3_PUBLIC_BASE_URL", "http://images.example.eu/stadtfest-images")

    with pytest.raises(SettingsError, match="S3_PUBLIC_BASE_URL"):
        load_settings()


def test_storage_credentials_are_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.delenv("S3_SECRET_ACCESS_KEY")

    with pytest.raises(SettingsError, match="S3_SECRET_ACCESS_KEY"):
        load_settings()


def _base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("GEOCODING_PROVIDER", "fake")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "fake")
    monkeypatch.delenv("WEB_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("WEB_SEARCH_BASE_URL", raising=False)


@pytest.mark.parametrize("provider", ["mistral", "openai", "anthropic"])
def test_llm_providers_with_keys_need_a_key(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    _base(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", provider)
    with pytest.raises(SettingsError, match="LLM_API_KEY"):
        load_settings()
    monkeypatch.setenv("LLM_API_KEY", "key")
    assert load_settings().llm_provider.value == provider


def test_ollama_needs_no_key_and_unknown_providers_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    _base(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert load_settings().llm_provider.value == "ollama"
    monkeypatch.setenv("LLM_PROVIDER", "gpt-local")
    with pytest.raises(SettingsError, match="LLM_PROVIDER"):
        load_settings()


def test_searxng_needs_its_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _base(monkeypatch)
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "searxng")
    with pytest.raises(SettingsError, match="WEB_SEARCH_BASE_URL"):
        load_settings()
    monkeypatch.setenv("WEB_SEARCH_BASE_URL", "http://searxng:8080")
    assert load_settings().web_search_provider.value == "searxng"


def test_brave_needs_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _base(monkeypatch)
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "brave")
    with pytest.raises(SettingsError, match="WEB_SEARCH_API_KEY"):
        load_settings()


def test_fake_ai_providers_are_rejected_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    _base(monkeypatch)
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("NOMINATIM_URL", "http://nominatim:8080")
    monkeypatch.setenv("GEOCODING_PROVIDER", "nominatim")
    _set_prod_auth(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    with pytest.raises(SettingsError, match="LLM_PROVIDER=fake"):
        load_settings()
