"""What the MCP adapter needs; satisfied structurally by `bootstrap.Container`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from stadtfest.application.ai_ingestion.use_cases import StartAiSearch
from stadtfest.application.events.use_cases import (
    GetPublicEvent,
    ListActiveCategories,
    SearchEvents,
)
from stadtfest.application.geocoding.use_cases import LocatePostalCode
from stadtfest.application.health.check_readiness import CheckReadiness
from stadtfest.application.identity.use_cases import Authenticate
from stadtfest.application.shared.ports import RateLimiter


class McpDependencies(Protocol):
    """Use cases called by the tools: the same instances the REST routers use."""

    check_readiness: CheckReadiness
    authenticate: Authenticate
    locate_postal_code: LocatePostalCode
    search_events: SearchEvents
    get_public_event: GetPublicEvent
    list_active_categories: ListActiveCategories
    start_ai_search: StartAiSearch
    rate_limiter: RateLimiter


@dataclass(frozen=True, slots=True)
class McpConfig:
    """Public addresses of the MCP server and its OAuth metadata (RFC 9728)."""

    public_url: str
    """Base URL clients reach the server under, e.g. `https://mcp.example.eu`."""
    authorization_server: str
    """Issuer of the IdP (Zitadel, locally Keycloak)."""
    link_base_url: str
    """Deep link domain for event links, e.g. `https://stadtfest.herderstreet.de`."""
    scopes: tuple[str, ...] = ("openid", "profile")
    """Scopes clients request; Zitadel needs the project audience scope as well."""
    path: str = "/mcp"

    @property
    def resource(self) -> str:
        """The protected resource: the MCP endpoint URL."""
        return self.public_url.rstrip("/") + self.path

    @property
    def resource_metadata_path(self) -> str:
        """Path of the Protected Resource Metadata (RFC 9728, path-suffixed form)."""
        return "/.well-known/oauth-protected-resource" + self.path

    @property
    def resource_metadata_url(self) -> str:
        """Absolute URL of the Protected Resource Metadata."""
        return self.public_url.rstrip("/") + self.resource_metadata_path

    def event_url(self, event_id: str) -> str:
        """Deep link that opens the event in the app (R04-US6)."""
        return f"{self.link_base_url.rstrip('/')}/f/{event_id}"
