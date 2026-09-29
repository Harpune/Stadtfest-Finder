"""Identity use cases: authenticate, own profile, delete account (R05)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from stadtfest.application.identity.claims import ClaimMapping, principal_from_claims
from stadtfest.application.identity.ports import (
    AccountJobQueue,
    IdpAdminPort,
    IdpUnavailableError,
    JobQueueUnavailableError,
    RegionDirectory,
    RegionRecord,
    TokenVerifier,
    UserRecord,
    UserRepository,
)
from stadtfest.application.shared.errors import InvalidInputError, ServiceUnavailableError
from stadtfest.domain.identity.account import InvalidNameError, name_from_claim, normalize_name
from stadtfest.domain.identity.principal import Principal, Role

logger = logging.getLogger(__name__)

AUTH_UNAVAILABLE = "auth_unavailable"
ACCOUNT_DELETION_UNAVAILABLE = "account_deletion_unavailable"


@dataclass(frozen=True, slots=True)
class MeView:
    """Own profile: stored names plus effective roles and region from the token."""

    id: str
    first_name: str = field(repr=False)
    last_name: str = field(repr=False)
    roles: list[Role]
    region: RegionRecord | None


class Authenticate:
    """Turn a bearer token into a `Principal`."""

    def __init__(self, verifier: TokenVerifier, mapping: ClaimMapping) -> None:
        """Create the use case."""
        self._verifier = verifier
        self._mapping = mapping

    async def __call__(self, token: str) -> Principal:
        """Validate the token and map its claims.

        Raises:
            InvalidTokenError: If the token is not valid.
            ServiceUnavailableError: If the IdP keys cannot be fetched.
        """
        try:
            claims = await self._verifier.verify(token)
        except IdpUnavailableError:
            raise ServiceUnavailableError(AUTH_UNAVAILABLE) from None
        return principal_from_claims(claims, self._mapping)


class _ProfileBuilder:
    def __init__(self, regions: RegionDirectory) -> None:
        self._regions = regions

    async def view(self, principal: Principal, user: UserRecord) -> MeView:
        region: RegionRecord | None = None
        roles = set(principal.roles)
        if principal.can_moderate and principal.region_key is not None:
            region = await self._regions.get_by_key(principal.region_key)
            if region is None:
                logger.warning("moderator_region_unknown")
                roles.discard(Role.MODERATOR)
        order = list(Role)
        return MeView(
            id=str(user.id),
            first_name=user.first_name,
            last_name=user.last_name,
            roles=sorted(roles, key=order.index),
            region=region,
        )


class GetMe:
    """Return the caller's profile, creating the account on the first call."""

    def __init__(self, users: UserRepository, regions: RegionDirectory) -> None:
        """Create the use case."""
        self._users = users
        self._profiles = _ProfileBuilder(regions)

    async def __call__(self, principal: Principal) -> MeView:
        """Upsert the user (names from the token) and return the profile."""
        user = await self._users.get_or_create(
            principal.subject,
            name_from_claim(principal.given_name),
            name_from_claim(principal.family_name),
        )
        return await self._profiles.view(principal, user)


class UpdateMe:
    """Change the caller's first and last name."""

    def __init__(self, users: UserRepository, regions: RegionDirectory) -> None:
        """Create the use case."""
        self._users = users
        self._profiles = _ProfileBuilder(regions)

    async def __call__(self, principal: Principal, first_name: str, last_name: str) -> MeView:
        """Validate and store the names.

        Raises:
            InvalidInputError: If a name is empty after trimming or too long.
        """
        problems: dict[str, str] = {}
        names: dict[str, str] = {}
        for field_name, value in (("firstName", first_name), ("lastName", last_name)):
            try:
                names[field_name] = normalize_name(value)
            except InvalidNameError:
                problems[field_name] = "invalid_length"
        if problems:
            raise InvalidInputError(problems)
        user = await self._users.update_name(
            principal.subject, names["firstName"], names["lastName"]
        )
        if user is None:
            # PATCH before the first GET: create the account with the entered names.
            user = await self._users.get_or_create(
                principal.subject, names["firstName"], names["lastName"]
            )
        return await self._profiles.view(principal, user)


class DeleteAccount:
    """Delete all personal data of the caller and the account at the IdP (Art. 17 GDPR)."""

    def __init__(self, users: UserRepository, idp: IdpAdminPort, jobs: AccountJobQueue) -> None:
        """Create the use case."""
        self._users = users
        self._idp = idp
        self._jobs = jobs

    async def __call__(self, principal: Principal) -> None:
        """Delete local data first, then the IdP account; retry the latter in the background.

        Raises:
            ServiceUnavailableError: If the IdP deletion failed and could not be scheduled.
                Local data is deleted already; repeating the request is safe.
        """
        await self._users.delete_personal_data(principal.subject)
        try:
            await self._idp.delete_user(principal.subject)
        except IdpUnavailableError:
            logger.warning("idp_deletion_deferred")
            try:
                await self._jobs.enqueue_idp_deletion(principal.subject)
            except JobQueueUnavailableError:
                logger.error("idp_deletion_enqueue_failed")
                raise ServiceUnavailableError(ACCOUNT_DELETION_UNAVAILABLE) from None


class DeleteIdpUser:
    """Worker step: delete a user at the IdP (retry of `DeleteAccount`, step 2)."""

    def __init__(self, idp: IdpAdminPort) -> None:
        """Create the use case."""
        self._idp = idp

    async def __call__(self, subject: str) -> None:
        """Delete the user at the IdP.

        Raises:
            IdpUnavailableError: If the IdP still fails; the worker retries later.
        """
        await self._idp.delete_user(subject)
