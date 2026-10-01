"""Outbound ports of the identity context."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

type Claims = Mapping[str, object]


class InvalidTokenError(Exception):
    """The token is malformed, expired, not yet valid or not signed by the IdP."""


class IdpUnavailableError(Exception):
    """The IdP (JWKS, admin API) cannot be reached or answered with a server error."""


class JobQueueUnavailableError(Exception):
    """A background job could not be enqueued."""


class DeletedAccountsUnavailableError(Exception):
    """The register of deleted accounts cannot be reached."""


class TokenVerifier(Protocol):
    """Validates access tokens issued by the IdP."""

    async def verify(self, token: str) -> Claims:
        """Check signature, issuer, audience and lifetime and return the claims.

        Raises:
            InvalidTokenError: If the token is not valid.
            IdpUnavailableError: If the signing keys cannot be fetched.
        """
        ...


@dataclass(frozen=True, slots=True)
class UserRecord:
    """Stored user account. Contains no email address (E-08)."""

    id: UUID
    first_name: str = field(repr=False)
    last_name: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class RegionRecord:
    """Moderation region as referenced from a profile."""

    id: UUID
    key: str
    name: str


class UserRepository(Protocol):
    """Persistence of user accounts and their personal data."""

    async def get_or_create(self, subject: str, first_name: str, last_name: str) -> UserRecord:
        """Return the user with this IdP subject, creating it with the given names if new."""
        ...

    async def update_name(self, subject: str, first_name: str, last_name: str) -> UserRecord | None:
        """Set the names of an existing user; None if the user does not exist."""
        ...

    async def delete_personal_data(self, subject: str) -> bool:
        """Delete the user and all its personal data in one transaction.

        Audit references (`created_by`, `updated_by`) are set to null. Later increments
        extend this method with their own data (favorites, lists, devices, ...).

        Returns:
            True if a user existed.
        """
        ...


class RegionDirectory(Protocol):
    """Read access to moderation regions."""

    async def get_by_key(self, key: str) -> RegionRecord | None:
        """Return the region with this key or None."""
        ...


class IdpAdminPort(Protocol):
    """Administrative access to the IdP (Zitadel Management API, Keycloak Admin API)."""

    async def delete_user(self, subject: str) -> None:
        """Delete the user at the IdP. Deleting a user that no longer exists succeeds.

        Raises:
            IdpUnavailableError: If the IdP cannot be reached or fails.
        """
        ...


class AccountJobQueue(Protocol):
    """Background jobs of the identity context."""

    async def enqueue_idp_deletion(self, subject: str) -> None:
        """Schedule a retried deletion of the user at the IdP.

        Raises:
            JobQueueUnavailableError: If the queue cannot be reached.
        """
        ...


class DeletedAccounts(Protocol):
    """Short-lived register of deleted accounts.

    Access tokens stay valid until they expire. Without this register a request with such
    a token right after the deletion would create the account again (`GET /v1/me`).
    """

    async def mark_deleted(self, subject: str, ttl_seconds: int) -> None:
        """Remember the subject as deleted for `ttl_seconds`.

        Raises:
            DeletedAccountsUnavailableError: If the register cannot be reached.
        """
        ...

    async def is_deleted(self, subject: str) -> bool:
        """Return True if the subject was deleted and its tokens may still be valid.

        Raises:
            DeletedAccountsUnavailableError: If the register cannot be reached.
        """
        ...
