import pytest

from stadtfest.application.identity.claims import ClaimMapping, principal_from_claims
from stadtfest.application.identity.ports import InvalidTokenError
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
    FakeDeletedAccounts,
    FakeIdpAdmin,
    FakeTokenVerifier,
    FakeUserRepository,
)

KEYCLOAK = ClaimMapping("realm_access.roles")
ZITADEL = ClaimMapping("urn:zitadel:iam:org:project:roles")


NOW = 1_800_000_000


def _principal(*roles: Role, given: str | None = "Lena", expires_at: int = NOW + 300) -> Principal:
    return Principal("sub-1", frozenset({Role.USER, *roles}), given, "Beispiel", expires_at)


def _delete_account(
    users: FakeUserRepository,
    idp: FakeIdpAdmin,
    jobs: FakeAccountJobs,
    deleted: FakeDeletedAccounts | None = None,
) -> DeleteAccount:
    return DeleteAccount(
        users,
        idp,
        jobs,
        deleted or FakeDeletedAccounts(),
        token_leeway_seconds=30,
        now=lambda: NOW,
    )


# --- claim mapping -----------------------------------------------------------------


def test_keycloak_claims_are_mapped() -> None:
    claims = {
        "sub": "kc-1",
        "realm_access": {"roles": ["user", "moderator", "offline_access"]},
        "given_name": "Mia",
        "family_name": "Moderatorin",
    }
    principal = principal_from_claims(claims, KEYCLOAK)
    assert principal.subject == "kc-1"
    assert principal.roles == {Role.USER, Role.MODERATOR}
    assert principal.can_moderate
    assert principal.given_name == "Mia"


def test_zitadel_claims_are_mapped() -> None:
    claims = {
        "sub": "2984",
        "urn:zitadel:iam:org:project:roles": {
            "moderator": {"123": "stadtfest.zitadel.cloud"},
            "category_admin": {"123": "stadtfest.zitadel.cloud"},
        },
    }
    principal = principal_from_claims(claims, ZITADEL)
    assert principal.roles == {Role.USER, Role.MODERATOR, Role.CATEGORY_ADMIN}


def test_every_authenticated_caller_is_a_user() -> None:
    principal = principal_from_claims({"sub": "x"}, KEYCLOAK)
    assert principal.roles == {Role.USER}
    assert not principal.can_moderate


def test_moderator_needs_no_region() -> None:
    """ADR 0015: the role alone allows moderation; a leftover region claim is ignored."""
    claims = {"sub": "kc-1", "realm_access": {"roles": ["moderator"]}}
    assert principal_from_claims(claims, KEYCLOAK).can_moderate
    with_region = principal_from_claims(claims | {"region": "ostalb"}, KEYCLOAK)
    assert with_region.can_moderate
    assert not hasattr(with_region, "region_key")


@pytest.mark.parametrize("claims", [{}, {"sub": ""}, {"sub": 42}])
def test_token_without_subject_is_invalid(claims: dict[str, object]) -> None:
    with pytest.raises(InvalidTokenError):
        principal_from_claims(claims, KEYCLOAK)


def test_principal_repr_contains_no_names() -> None:
    assert "Lena" not in repr(_principal())


# --- authenticate --------------------------------------------------------------------


async def test_authenticate_maps_verified_claims() -> None:
    verifier = FakeTokenVerifier({"t": {"sub": "s", "realm_access": {"roles": ["user"]}}})
    principal = await Authenticate(verifier, KEYCLOAK, FakeDeletedAccounts())("t")
    assert principal.subject == "s"


async def test_authenticate_rejects_invalid_tokens() -> None:
    with pytest.raises(InvalidTokenError):
        await Authenticate(FakeTokenVerifier(), KEYCLOAK, FakeDeletedAccounts())("forged")


async def test_authenticate_reports_unavailable_idp() -> None:
    with pytest.raises(ServiceUnavailableError):
        await Authenticate(FakeTokenVerifier(unavailable=True), KEYCLOAK, FakeDeletedAccounts())(
            "t"
        )


# --- get / update me -------------------------------------------------------------------


async def test_first_call_creates_the_user_with_names_from_the_token() -> None:
    users = FakeUserRepository()
    me = await GetMe(users)(_principal())
    assert (me.first_name, me.last_name) == ("Lena", "Beispiel")
    assert me.roles == [Role.USER]
    assert me.id == str(users.users["sub-1"].id)


async def test_second_call_keeps_the_stored_names() -> None:
    users = FakeUserRepository()
    get_me = GetMe(users)
    first = await get_me(_principal())
    await UpdateMe(users)(_principal(), "Magdalena", "B")
    again = await get_me(_principal(given="Lena"))
    assert again.id == first.id
    assert again.first_name == "Magdalena"


async def test_missing_given_name_is_stored_empty() -> None:
    me = await GetMe(FakeUserRepository())(_principal(given=None))
    assert me.first_name == ""


async def test_moderator_profile_lists_the_role() -> None:
    me = await GetMe(FakeUserRepository())(_principal(Role.MODERATOR))
    assert me.roles == [Role.USER, Role.MODERATOR]


async def test_update_trims_names() -> None:
    users = FakeUserRepository()
    me = await UpdateMe(users)(_principal(), "  Lena ", " Muster ")
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
        await UpdateMe(FakeUserRepository())(_principal(), first, last)
    assert set(error.value.fields) == invalid


# --- delete account ----------------------------------------------------------------


async def test_delete_account_removes_local_data_and_idp_user() -> None:
    users, idp, jobs = FakeUserRepository(), FakeIdpAdmin(), FakeAccountJobs()
    await GetMe(users)(_principal())

    await _delete_account(users, idp, jobs)(_principal())

    assert users.users == {}
    assert idp.deleted == ["sub-1"]
    assert jobs.enqueued == []


async def test_delete_account_retries_idp_deletion_in_background() -> None:
    users, idp, jobs = FakeUserRepository(), FakeIdpAdmin(unavailable=True), FakeAccountJobs()
    await GetMe(users)(_principal())

    await _delete_account(users, idp, jobs)(_principal())

    assert users.users == {}
    assert jobs.enqueued == ["sub-1"]


async def test_delete_account_fails_if_retry_cannot_be_scheduled() -> None:
    users = FakeUserRepository()
    idp, jobs = FakeIdpAdmin(unavailable=True), FakeAccountJobs(unavailable=True)
    await GetMe(users)(_principal())

    with pytest.raises(ServiceUnavailableError):
        await _delete_account(users, idp, jobs)(_principal())
    assert users.users == {}  # local data is deleted first; repeating is safe


async def test_delete_account_without_local_user_still_deletes_at_idp() -> None:
    idp = FakeIdpAdmin()
    await _delete_account(FakeUserRepository(), idp, FakeAccountJobs())(_principal())
    assert idp.deleted == ["sub-1"]


async def test_delete_account_blocks_the_token_until_it_expires() -> None:
    deleted = FakeDeletedAccounts()
    await _delete_account(FakeUserRepository(), FakeIdpAdmin(), FakeAccountJobs(), deleted)(
        _principal()
    )
    assert deleted.marked == {"sub-1": 300 + 30}  # remaining lifetime plus leeway


async def test_still_valid_token_cannot_recreate_a_deleted_account() -> None:
    verifier = FakeTokenVerifier({"t": {"sub": "sub-1", "exp": NOW + 300}})
    deleted = FakeDeletedAccounts()
    users = FakeUserRepository()
    authenticate = Authenticate(verifier, KEYCLOAK, deleted)
    await _delete_account(users, FakeIdpAdmin(), FakeAccountJobs(), deleted)(
        await authenticate("t")
    )

    with pytest.raises(InvalidTokenError):
        await authenticate("t")
    assert users.users == {}


async def test_expired_token_needs_no_block() -> None:
    deleted = FakeDeletedAccounts()
    await _delete_account(FakeUserRepository(), FakeIdpAdmin(), FakeAccountJobs(), deleted)(
        _principal(expires_at=NOW - 60)
    )
    assert deleted.marked == {}


async def test_delete_account_succeeds_without_the_register(
    caplog: pytest.LogCaptureFixture,
) -> None:
    users, idp = FakeUserRepository(), FakeIdpAdmin()
    await GetMe(users)(_principal())

    await _delete_account(users, idp, FakeAccountJobs(), FakeDeletedAccounts(unavailable=True))(
        _principal()
    )

    assert users.users == {}
    assert idp.deleted == ["sub-1"]
    assert "deleted_accounts_unavailable" in caplog.text


async def test_authenticate_fails_open_without_the_register() -> None:
    verifier = FakeTokenVerifier({"t": {"sub": "s"}})
    principal = await Authenticate(verifier, KEYCLOAK, FakeDeletedAccounts(unavailable=True))("t")
    assert principal.subject == "s"


def test_token_expiry_is_mapped() -> None:
    principal = principal_from_claims({"sub": "s", "exp": NOW}, KEYCLOAK)
    assert principal.expires_at == NOW


async def test_delete_idp_user_delegates_to_the_port() -> None:
    idp = FakeIdpAdmin()
    await DeleteIdpUser(idp)("sub-9")
    assert idp.deleted == ["sub-9"]
