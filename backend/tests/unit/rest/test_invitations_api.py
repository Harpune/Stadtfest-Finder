"""REST adapter tests for the invitation endpoints and `invitationSummary` (R14)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from stadtfest.adapters.inbound.rest import events, invitations
from stadtfest.adapters.inbound.rest.auth import optional_principal
from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.application.collections.invitations import (
    AcceptInvitationLink,
    CreateInvitationLink,
    GetHostInvitation,
    GetInvitationSummary,
    GetReceivedInvitation,
    InviteFriends,
    ListReceivedInvitations,
    LookUpInvitationLink,
    RemindInvitees,
    RespondToInvitation,
)
from stadtfest.application.collections.use_cases import IsFavorite
from stadtfest.application.events.use_cases import GetPublicEvent
from stadtfest.application.identity.claims import ClaimMapping
from stadtfest.application.identity.use_cases import Authenticate
from stadtfest.domain.events.event import EventStatus
from tests.fakes import (
    FakeAccountResolver,
    FakeDeletedAccounts,
    FakeEventCatalog,
    FakeFavoriteRepository,
    FakeFriendRepository,
    FakeInvitationRepository,
    FakeRateLimiter,
    FakeTokenVerifier,
    FixedClock,
)
from tests.unit.rest.test_catalog_api import TODAY, _detail, _summary

LENA_ID, TIM_ID = (uuid5(NAMESPACE_URL, f"sub-{n}") for n in ("lena", "tim"))
LENA = {"Authorization": "Bearer lena"}
TIM = {"Authorization": "Bearer tim"}
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
EVENT = replace(_summary("Reichsstädter Tage"), status=EventStatus.PUBLISHED)


@pytest.fixture
def repository() -> FakeInvitationRepository:
    people = {LENA_ID: ("Lena", "Berg"), TIM_ID: ("Tim", "Kurz")}
    return FakeInvitationRepository(public_events={EVENT.id: EVENT}, people=people)


@pytest.fixture
def client(repository: FakeInvitationRepository) -> TestClient:
    verifier = FakeTokenVerifier(
        {
            "lena": {"sub": "sub-lena", "realm_access": {"roles": []}},
            "tim": {"sub": "sub-tim", "realm_access": {"roles": []}},
        }
    )
    friends = FakeFriendRepository(people=repository.people)
    friends.friendships[frozenset({LENA_ID, TIM_ID})] = NOW
    accounts = FakeAccountResolver()
    clock = FixedClock(TODAY)
    limiter = FakeRateLimiter()
    app = FastAPI(dependencies=[Depends(optional_principal)])
    register_error_handlers(app)
    app.include_router(events.router)
    app.include_router(invitations.router)
    app.state.container = SimpleNamespace(
        authenticate=Authenticate(
            verifier, ClaimMapping("realm_access.roles"), FakeDeletedAccounts()
        ),
        get_public_event=GetPublicEvent(FakeEventCatalog(details={EVENT.id: _detail(EVENT.id)})),
        is_favorite=IsFavorite(FakeFavoriteRepository()),
        get_host_invitation=GetHostInvitation(repository, accounts),
        invite_friends=InviteFriends(repository, friends, accounts, clock, lambda: NOW),
        create_invitation_link=CreateInvitationLink(repository, accounts, clock),
        remind_invitees=RemindInvitees(repository, accounts, lambda: NOW),
        respond_to_invitation=RespondToInvitation(repository, accounts, clock, lambda: NOW),
        list_received_invitations=ListReceivedInvitations(repository, accounts),
        get_received_invitation=GetReceivedInvitation(repository, accounts),
        look_up_invitation_link=LookUpInvitationLink(repository, accounts, limiter),
        accept_invitation_link=AcceptInvitationLink(
            repository, friends, accounts, limiter, clock, lambda: NOW
        ),
        get_invitation_summary=GetInvitationSummary(repository, accounts),
    )
    return TestClient(app)


def test_endpoints_require_a_token(client: TestClient) -> None:
    assert client.get(f"/v1/events/{EVENT.id}/invitation").status_code == 401
    assert client.get("/v1/me/invitations").status_code == 401


def test_invite_answer_and_summary(client: TestClient) -> None:
    base = f"/v1/events/{EVENT.id}/invitation"
    assert client.get(base, headers=LENA).status_code == 404
    created = client.post(
        f"{base}/invitees",
        json={"userIds": [str(TIM_ID)], "message": "Kommst du mit?"},
        headers=LENA,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["message"] == "Kommst du mit?"
    assert body["invitees"][0]["person"]["firstName"] == "Tim"
    assert body["invitees"][0]["status"] == "open"

    invitation = body["id"]
    received = client.get(f"/v1/me/invitations/{invitation}", headers=TIM).json()
    assert received["host"] == {"id": str(LENA_ID), "firstName": "Lena", "lastName": "Berg"}
    answered = client.put(
        f"/v1/invitations/{invitation}/response", json={"status": "accepted"}, headers=TIM
    )
    assert answered.status_code == 200
    assert answered.json()["status"] == "accepted"
    assert [i["id"] for i in client.get("/v1/me/invitations", headers=TIM).json()] == [invitation]

    detail = client.get(f"/v1/events/{EVENT.id}", headers=LENA).json()
    assert detail["invitationSummary"] == {
        "invitationId": invitation,
        "role": "host",
        "people": [{"id": str(TIM_ID), "firstName": "Tim", "lastName": "Kurz"}],
    }
    assert "invitationSummary" not in client.get(f"/v1/events/{EVENT.id}").json()


def test_errors_use_the_common_format(client: TestClient) -> None:
    stranger = uuid4()
    response = client.post(
        f"/v1/events/{EVENT.id}/invitation/invitees",
        json={"userIds": [str(stranger)]},
        headers=LENA,
    )
    assert response.status_code == 422
    assert response.json()["error"] == "not_a_friend"

    invitation = client.post(
        f"/v1/events/{EVENT.id}/invitation/invitees",
        json={"userIds": [str(TIM_ID)]},
        headers=LENA,
    ).json()["id"]
    assert client.post(f"/v1/invitations/{invitation}/reminders", headers=LENA).json() == {
        "reminded": 1
    }
    again = client.post(f"/v1/invitations/{invitation}/reminders", headers=LENA)
    assert again.status_code == 429
    assert again.json()["error"] == "reminded_recently"
    assert again.json()["fields"]["retryAfter"] == str(24 * 3600 + 1)


def test_link_preview_and_accept(client: TestClient) -> None:
    token = client.post(f"/v1/events/{EVENT.id}/invitation/link", headers=LENA).json()["token"]
    preview = client.get(f"/v1/invitation-links/{token}", headers=TIM).json()
    assert preview["host"] == {"firstName": "Lena", "lastNameInitial": "B"}
    assert preview["own"] is False
    accepted = client.post(f"/v1/invitation-links/{token}/accept", headers=TIM)
    assert accepted.status_code == 201
    assert accepted.json()["status"] == "open"
    own = client.post(f"/v1/invitation-links/{token}/accept", headers=LENA)
    assert own.json()["error"] == "self_link"
    assert client.get("/v1/invitation-links/short", headers=TIM).status_code == 422
