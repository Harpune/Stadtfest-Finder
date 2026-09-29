"""The authenticated caller as seen by use cases (flow B)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    """Roles assigned at the IdP (ADR 0003)."""

    USER = "user"
    MODERATOR = "moderator"
    CATEGORY_ADMIN = "category_admin"


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated caller, created from a validated access token.

    Authorization checks in use cases rely on this object only, so REST, MCP and the
    worker enforce the same rules. Names are excluded from `repr` so that they never end
    up in logs or tracebacks.

    Attributes:
        subject: Stable user ID at the IdP (`sub` claim).
        roles: Effective roles. `moderator` is only present together with a region.
        region_key: Moderation region (e.g. `ostalb`), None for non-moderators.
        given_name: First name from the token, used when the account is created.
        family_name: Last name from the token, used when the account is created.
    """

    subject: str
    roles: frozenset[Role]
    region_key: str | None = None
    given_name: str | None = field(default=None, repr=False)
    family_name: str | None = field(default=None, repr=False)

    def has_role(self, role: Role) -> bool:
        """Return True if the principal has the given role."""
        return role in self.roles

    @property
    def can_moderate(self) -> bool:
        """Whether the principal may maintain events of its region."""
        return Role.MODERATOR in self.roles and self.region_key is not None
