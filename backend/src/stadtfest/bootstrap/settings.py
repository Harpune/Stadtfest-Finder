"""Application settings loaded from the environment and validated at startup."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import (
    AnyHttpUrl,
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    ValidationError,
    model_validator,
)
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


class IdpAdminProvider(StrEnum):
    """IdP admin adapter for account deletion (R05). `fake` is only allowed in dev and test."""

    KEYCLOAK = "keycloak"
    ZITADEL = "zitadel"
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
    auth_issuer: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://localhost:58080/realms/stadtfest"),
        description="Expected `iss` of access tokens; must match the URL the app logs in at",
    )
    auth_audience: str = Field(default="stadtfest-api", min_length=1)
    auth_jwks_url: AnyHttpUrl | None = Field(
        default=None, description="JWKS endpoint; discovered from the issuer if unset"
    )
    auth_roles_claim: str = Field(default="realm_access.roles", min_length=1)
    auth_region_claim: str = Field(default="region", min_length=1)
    auth_leeway_seconds: int = Field(default=30, ge=0, le=300)
    auth_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    idp_admin_provider: IdpAdminProvider = IdpAdminProvider.FAKE
    idp_admin_client_id: str | None = None
    idp_admin_client_secret: SecretStr | None = None
    idp_admin_token: SecretStr | None = None
    s3_endpoint_url: AnyHttpUrl = Field(
        description="S3 endpoint the backend uses, e.g. http://seaweedfs:8333 (ADR 0007)"
    )
    s3_presign_endpoint_url: AnyHttpUrl | None = Field(
        default=None,
        description="Endpoint in signed upload URLs if the app reaches the storage differently",
    )
    s3_public_base_url: AnyHttpUrl = Field(
        description="URL under which the bucket's public/ prefix is readable, incl. bucket"
    )
    s3_bucket: str = Field(default="stadtfest-images", min_length=3, max_length=63)
    s3_region: str = Field(default="eu-central-1", min_length=1)
    s3_access_key_id: str = Field(min_length=1)
    s3_secret_access_key: SecretStr
    s3_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    @model_validator(mode="after")
    def _check_adapters(self) -> Settings:
        if self.geocoding_provider is GeocodingProvider.FAKE and self.env is Environment.PROD:
            raise ValueError("GEOCODING_PROVIDER=fake is not allowed in prod")
        if self.geocoding_provider is GeocodingProvider.NOMINATIM and self.nominatim_url is None:
            raise ValueError("NOMINATIM_URL is required for GEOCODING_PROVIDER=nominatim")
        self._check_auth()
        if self.env is Environment.PROD and self.s3_public_base_url.scheme != "https":
            raise ValueError("S3_PUBLIC_BASE_URL must use https in prod")
        return self

    def _check_auth(self) -> None:
        if self.env is Environment.PROD:
            if self.auth_issuer.scheme != "https":
                raise ValueError("AUTH_ISSUER must use https in prod")
            if self.idp_admin_provider is IdpAdminProvider.FAKE:
                raise ValueError("IDP_ADMIN_PROVIDER=fake is not allowed in prod")
        if self.idp_admin_provider is IdpAdminProvider.KEYCLOAK and not (
            self.idp_admin_client_id and self.idp_admin_client_secret
        ):
            raise ValueError(
                "IDP_ADMIN_CLIENT_ID and IDP_ADMIN_CLIENT_SECRET are required for "
                "IDP_ADMIN_PROVIDER=keycloak"
            )
        if self.idp_admin_provider is IdpAdminProvider.ZITADEL and not self.idp_admin_token:
            raise ValueError("IDP_ADMIN_TOKEN is required for IDP_ADMIN_PROVIDER=zitadel")

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
