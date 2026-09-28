import pytest

from stadtfest.bootstrap.settings import Environment, SettingsError, load_settings


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

    settings = load_settings()

    assert settings.env is Environment.PROD
    assert settings.is_production
