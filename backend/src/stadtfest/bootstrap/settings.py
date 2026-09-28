"""Application settings loaded from the environment and validated at startup."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment. Fake adapters are only allowed outside production."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


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
            f"{'.'.join(str(part) for part in error['loc']).upper()}: {error['type']}"
            for error in exc.errors()
        )
        raise SettingsError("Invalid configuration: " + "; ".join(problems)) from None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return load_settings()
