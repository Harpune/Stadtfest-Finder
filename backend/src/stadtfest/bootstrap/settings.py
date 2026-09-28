"""Application settings loaded from the environment and validated at startup."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment. Fake adapters are only allowed outside production."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class GeocodingProvider(StrEnum):
    """Geocoding adapter (ADR 0006). `fake` is only allowed in dev and test."""

    NOMINATIM = "nominatim"
    FAKE = "fake"


class LogFormat(StrEnum):
    """Log output format."""

    JSON = "json"
    CONSOLE = "console"


class Settings(BaseSettings):
    """All runtime configuration. Every variable is documented in `.env.example`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: Environment = Environment.DEV
    database_url: PostgresDsn = Field(
        description="SQLAlchemy URL, e.g. postgresql+asyncpg://user:pass@host:5432/db",
    )
    redis_url: RedisDsn = Field(description="Redis URL, e.g. redis://localhost:6379/0")
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR)$")
    log_format: LogFormat = LogFormat.JSON
    geocoding_provider: GeocodingProvider = GeocodingProvider.NOMINATIM
    nominatim_url: AnyHttpUrl | None = Field(
        default=None,
        description="Base URL of the self-hosted Nominatim, e.g. http://nominatim:8080",
    )
    geocoding_timeout_seconds: float = Field(default=3.0, gt=0, le=30)

    @model_validator(mode="after")
    def _check_adapters(self) -> Settings:
        if self.geocoding_provider is GeocodingProvider.FAKE and self.env is Environment.PROD:
            raise ValueError("GEOCODING_PROVIDER=fake is not allowed in prod")
        if self.geocoding_provider is GeocodingProvider.NOMINATIM and self.nominatim_url is None:
            raise ValueError("NOMINATIM_URL is required for GEOCODING_PROVIDER=nominatim")
        return self

    @property
    def is_production(self) -> bool:
        """Whether the app runs in production."""
        return self.env is Environment.PROD


class SettingsError(RuntimeError):
    """Raised when the environment does not contain a valid configuration."""


def load_settings() -> Settings:
    """Load and validate settings, failing fast with the names of invalid variables.

    Values are never included in the error message, because they may contain secrets.

    Returns:
        The validated settings.

    Raises:
        SettingsError: If a required variable is missing or invalid.
    """
    try:
        return Settings()
    except ValidationError as exc:
        problems = sorted(
            # Model-level errors have no location; their message names the variable, not a value.
            f"{'.'.join(str(part) for part in error['loc']).upper()}: {error['type']}"
            if error["loc"]
            else str(error["msg"]).removeprefix("Value error, ")
            for error in exc.errors()
        )
        raise SettingsError("Invalid configuration: " + "; ".join(problems)) from None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return load_settings()
