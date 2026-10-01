"""Mapping of IdP token claims to a `Principal` (Keycloak and Zitadel formats, ADR 0003)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from stadtfest.application.identity.ports import Claims, InvalidTokenError
from stadtfest.domain.identity.principal import Principal, Role

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClaimMapping:
    """Names of the role and region claims (`AUTH_ROLES_CLAIM`, `AUTH_REGION_CLAIM`).

    A name is first looked up as a literal key (Zitadel: `urn:zitadel:iam:org:project:roles`),
    then as a dotted path (Keycloak: `realm_access.roles`).
    """

    roles_claim: str
    region_claim: str


def _lookup(claims: Claims, name: str) -> object:
    if name in claims:
        return claims[name]
    current: object = claims
    for part in name.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _role_names(value: object) -> list[str]:
    # Keycloak: ["user", "moderator"]; Zitadel: {"moderator": {"<orgId>": "<domain>"}}.
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, dict):
        return [key for key in value if isinstance(key, str)]
    if isinstance(value, str):
        return [value]
    return []


def _region_key(value: object) -> str | None:
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: object) -> int | None:
    # bool is a subclass of int but never a valid timestamp.
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def principal_from_claims(claims: Claims, mapping: ClaimMapping) -> Principal:
    """Build the principal from validated claims.

    Unknown roles are ignored. Every authenticated caller has the role `user`. A moderator
    without region loses the moderation role; a warning without user data is logged.

    Args:
        claims: Claims of a validated access token.
        mapping: Configured claim names.

    Returns:
        The principal.

    Raises:
        InvalidTokenError: If the token has no subject.
    """
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidTokenError
    known = {role.value for role in Role}
    roles = {
        Role(name) for name in _role_names(_lookup(claims, mapping.roles_claim)) if name in known
    }
    roles.add(Role.USER)
    region_key = _region_key(_lookup(claims, mapping.region_claim))
    if Role.MODERATOR in roles and region_key is None:
        logger.warning("moderator_without_region")
        roles.discard(Role.MODERATOR)
    return Principal(
        subject=subject,
        roles=frozenset(roles),
        region_key=region_key if Role.MODERATOR in roles else None,
        given_name=_optional_str(claims.get("given_name")),
        family_name=_optional_str(claims.get("family_name")),
        expires_at=_optional_int(claims.get("exp")),
    )
