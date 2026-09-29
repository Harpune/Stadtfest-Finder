import logging
from uuid import uuid4

import pytest

from stadtfest.application.identity.claims import ClaimMapping, principal_from_claims
from stadtfest.application.identity.ports import InvalidTokenError, RegionRecord
from stadtfest.application.identity.use_cases import (
    Authenticate,
    DeleteAccount,
    DeleteIdpUser,
    GetMe,
    UpdateMe,
)
from stadtfest.application.shared.errors import InvalidInputError, ServiceUnavailableError
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import (
    FakeAccountJobs,
    FakeIdpAdmin,
    FakeRegionDirectory,
    FakeTokenVerifier,
    FakeUserRepository,
)

KEYCLOAK = ClaimMapping("realm_access.roles", "region")
ZITADEL = ClaimMapping("urn:zitadel:iam:org:project:roles", "region")
OSTALB = RegionRecord(uuid4(), "ostalb", "Ostalbkreis")


def _principal(*roles: Role, region: str | None = None, given: str | None = "Lena") -> Principal:
    return Principal("sub-1", frozenset({Role.USER, *roles}), region, given, "Beispiel")


# --- claim mapping -----------------------------------------------------------------


def test_keycloak_claims_are_mapped() -> None:
    claims = {
        "sub": "kc-1",
        "realm_access": {"roles": ["user", "moderator", "offline_access"]},
        "region": "ostalb",
        "given_name": "Mia",
        "family_name": "Moderatorin",
    }
    principal = principal_from_claims(claims, KEYCLOAK)
    assert principal.subject == "kc-1"
    assert principal.roles == {Role.USER, Role.MODERATOR}
    assert principal.region_key == "ostalb"
    assert principal.can_moderate
    assert principal.given_name == "Mia"


def test_zitadel_claims_are_mapped() -> None:
    claims = {
        "sub": "2984",
        "urn:zitadel:iam:org:project:roles": {
            "moderator": {"123": "stadtfest.zitadel.cloud"},
            "category_admin": {"123": "stadtfest.zitadel.cloud"},
        },
        "region": "ostalb",
    }
    principal = principal_from_claims(claims, ZITADEL)
    assert principal.roles == {Role.USER, Role.MODERATOR, Role.CATEGORY_ADMIN}
    assert principal.region_key == "ostalb"


def test_every_authenticated_caller_is_a_user() -> None:
    principal = principal_from_claims({"sub": "x"}, KEYCLOAK)
    assert principal.roles == {Role.USER}
    assert not principal.can_moderate


def test_moderator_without_region_loses_moderation_rights(
    caplog: pytest.LogCaptureFixture,
) -> None:
    claims = {"sub": "kc-1", "realm_access": {"roles": ["moderator"]}, "email": "m@x.test"}
    with caplog.at_level(logging.WARNING):
        principal = principal_from_claims(claims, KEYCLOAK)
    assert Role.MODERATOR not in principal.roles
    assert not principal.can_moderate
    assert "moderator_without_region" in caplog.text
    assert "kc-1" not in caplog.text
    assert "m@x.test" not in caplog.text


def test_region_of_non_moderators_is_ignored() -> None:
    principal = principal_from_claims({"sub": "x", "region": "ostalb"}, KEYCLOAK)
    assert principal.region_key is None


def test_single_valued_region_list_is_accepted() -> None:
    claims = {"sub": "x", "realm_access": {"roles": ["moderator"]}, "region": ["ostalb"]}
    assert principal_from_claims(claims, KEYCLOAK).region_key == "ostalb"


@pytest.mark.parametrize("claims", [{}, {"sub": ""}, {"sub": 42}])
def test_token_without_subject_is_invalid(claims: dict[str, object]) -> None:
    with pytest.raises(InvalidTokenError):
        principal_from_claims(claims, KEYCLOAK)


def test_principal_repr_contains_no_names() -> None:
    assert "Lena" not in repr(_principal())


# --- authenticate --------------------------------------------------------------------


async def test_authenticate_maps_verified_claims() -> None:
    verifier = FakeTokenVerifier({"t": {"sub": "s", "realm_access": {"roles": ["user"]}}})
    principal = await Authenticate(verifier, KEYCLOAK)("t")
    assert principal.subject == "s"


async def test_authenticate_rejects_invalid_tokens() -> None:
    with pytest.raises(InvalidTokenError):
        await Authenticate(FakeTokenVerifier(), KEYCLOAK)("forged")


async def test_authenticate_reports_unavailable_idp() -> None:
    with pytest.raises(ServiceUnavailableError):
        await Authenticate(FakeTokenVerifier(unavailable=True), KEYCLOAK)("t")


# --- get / update me -------------------------------------------------------------------


async def test_first_call_creates_the_user_with_names_from_the_token() -> None:
    users = FakeUserRepository()
    me = await GetMe(users, FakeRegionDirectory())(_principal())
    assert (me.first_name, me.last_name) == ("Lena", "Beispiel")
    assert me.roles == [Role.USER]
    assert me.region is None
    assert me.id == str(users.users["sub-1"].id)


async def test_second_call_keeps_the_stored_names() -> None:
    users = FakeUserRepository()
    get_me = GetMe(users, FakeRegionDirectory())
    first = await get_me(_principal())
    await UpdateMe(users, FakeRegionDirectory())(_principal(), "Magdalena", "B")
    again = await get_me(_principal(given="Lena"))
    assert again.id == first.id
    assert again.first_name == "Magdalena"


async def test_missing_given_name_is_stored_empty() -> None:
    me = await GetMe(FakeUserRepository(), FakeRegionDirectory())(_principal(given=None))
    assert me.first_name == ""


async def test_moderator_profile_contains_the_region() -> None:
    regions = FakeRegionDirectory({"ostalb": OSTALB})
    me = await GetMe(FakeUserRepository(), regions)(_principal(Role.MODERATOR, region="ostalb"))
    assert me.roles == [Role.USER, Role.MODERATOR]
    assert me.region == OSTALB


async def test_moderator_with_unknown_region_gets_no_moderation_role() -> None:
    me = await GetMe(FakeUserRepository(), FakeRegionDirectory())(
        _principal(Role.MODERATOR, region="nowhere")
    )
    assert me.roles == [Role.USER]
    assert me.region is None


async def test_update_trims_names() -> None:
    users = FakeUserRepository()
    me = await UpdateMe(users, FakeRegionDirectory())(_principal(), "  Lena ", " Muster ")
    assert (me.first_name, me.last_name) == ("Lena", "Muster")


@pytest.mark.parametrize(
    ("first", "last", "invalid"),
    [
        ("  ", "Muster", {"firstName"}),
        ("Lena", "x" * 51, {"lastName"}),
        ("", "", {"firstName", "lastName"}),
    ],
)
async def test_update_rejects_invalid_names(first: str, last: str, invalid: set[str]) -> None:
    with pytest.raises(InvalidInputError) as error:
        await UpdateMe(FakeUserRepository(), FakeRegionDirectory())(_principal(), first, last)
    assert set(error.value.fields) == invalid


# --- delete account ----------------------------------------------------------------


async def test_delete_account_removes_local_data_and_idp_user() -> None:
    users, idp, jobs = FakeUserRepository(), FakeIdpAdmin(), FakeAccountJobs()
    await GetMe(users, FakeRegionDirectory())(_principal())

    await DeleteAccount(users, idp, jobs)(_principal())

    assert users.users == {}
    assert idp.deleted == ["sub-1"]
    assert jobs.enqueued == []


async def test_delete_account_retries_idp_deletion_in_background() -> None:
    users, idp, jobs = FakeUserRepository(), FakeIdpAdmin(unavailable=True), FakeAccountJobs()
    await GetMe(users, FakeRegionDirectory())(_principal())

    await DeleteAccount(users, idp, jobs)(_principal())

    assert users.users == {}
    assert jobs.enqueued == ["sub-1"]


async def test_delete_account_fails_if_retry_cannot_be_scheduled() -> None:
    users = FakeUserRepository()
    idp, jobs = FakeIdpAdmin(unavailable=True), FakeAccountJobs(unavailable=True)
    await GetMe(users, FakeRegionDirectory())(_principal())

    with pytest.raises(ServiceUnavailableError):
        await DeleteAccount(users, idp, jobs)(_principal())
    assert users.users == {}  # local data is deleted first; repeating is safe


async def test_delete_account_without_local_user_still_deletes_at_idp() -> None:
    idp = FakeIdpAdmin()
    await DeleteAccount(FakeUserRepository(), idp, FakeAccountJobs())(_principal())
    assert idp.deleted == ["sub-1"]


async def test_delete_idp_user_delegates_to_the_port() -> None:
    idp = FakeIdpAdmin()
    await DeleteIdpUser(idp)("sub-9")
    assert idp.deleted == ["sub-9"]
