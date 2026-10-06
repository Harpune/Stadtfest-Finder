"""Push adapters against HTTP stubs: no real Expo, APNs or FCM (R11)."""

from __future__ import annotations

import json

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from stadtfest.adapters.outbound.push.direct import ApnsConfig, DirectPushSender, FcmConfig
from stadtfest.adapters.outbound.push.disabled import DisabledPushSender
from stadtfest.adapters.outbound.push.expo import ExpoPushSender
from stadtfest.application.notifications.ports import (
    DevicePlatform,
    PushMessage,
    PushUnavailableError,
)


def _message(token: str, platform: DevicePlatform = DevicePlatform.ANDROID) -> PushMessage:
    return PushMessage(
        token=token,
        platform=platform,
        title="Fest abgesagt",
        body="Eines deiner Lieblingsfeste fällt aus.",
        badge=2,
        data={"notificationId": "n1", "type": "cancel", "targetType": "event", "targetId": "e1"},
    )


def _pem(key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


async def test_disabled_sends_nothing() -> None:
    sender = DisabledPushSender()
    assert (await sender.send([_message("t")])).invalid_tokens == frozenset()
    assert await sender.check_receipts({"x": "t"}) == frozenset()


async def test_expo_sends_batches_and_reports_invalid_tokens() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/getReceipts"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "ticket-ok": {"status": "ok"},
                        "ticket-late": {
                            "status": "error",
                            "details": {"error": "DeviceNotRegistered"},
                        },
                    }
                },
            )
        body = json.loads(request.content)
        tickets = [
            {"status": "error", "details": {"error": "DeviceNotRegistered"}}
            if message["to"] == "ExponentPushToken[gone]"
            else {"status": "ok", "id": f"ticket-{message['to']}"}
            for message in body
        ]
        return httpx.Response(200, json={"data": tickets})

    sender = ExpoPushSender(httpx.AsyncClient(transport=httpx.MockTransport(handler)), "secret")
    tokens = [f"ExponentPushToken[{i}]" for i in range(150)] + ["ExponentPushToken[gone]"]

    result = await sender.send([_message(token) for token in tokens])

    assert result.invalid_tokens == {"ExponentPushToken[gone]"}
    assert len(result.receipts) == 150
    assert [len(json.loads(r.content)) for r in requests] == [100, 51]
    first = json.loads(requests[0].content)[0]
    assert first["badge"] == 2
    assert first["channelId"] == "default"
    assert first["data"]["targetId"] == "e1"
    assert requests[0].headers["authorization"] == "Bearer secret"

    invalid = await sender.check_receipts({"ticket-ok": "a", "ticket-late": "b", "ticket-x": "c"})
    assert invalid == {"b"}


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(429, json={"errors": [{"code": "TOO_MANY_REQUESTS"}]}),
        httpx.Response(500),
        httpx.Response(200, json={"errors": [{"code": "PUSH_TOO_MANY_EXPERIENCE_IDS"}]}),
    ],
)
async def test_expo_request_errors_mean_unavailable(response: httpx.Response) -> None:
    sender = ExpoPushSender(
        httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)), None
    )
    with pytest.raises(PushUnavailableError):
        await sender.send([_message("ExponentPushToken[a]")])


@pytest.fixture
def keys() -> tuple[ec.EllipticCurvePrivateKey, rsa.RSAPrivateKey]:
    return ec.generate_private_key(ec.SECP256R1()), rsa.generate_private_key(65537, 2048)


def _direct(
    handler: httpx.MockTransport, keys: tuple[ec.EllipticCurvePrivateKey, rsa.RSAPrivateKey]
) -> DirectPushSender:
    apns_key, fcm_key = keys
    return DirectPushSender(
        httpx.AsyncClient(transport=handler),
        ApnsConfig("KEY123", "TEAM456", _pem(apns_key), "de.stadtfestfinder.app"),
        FcmConfig("stadtfest", "push@stadtfest.iam", _pem(fcm_key), "https://oauth2.test/token"),
        clock=lambda: 1_800_000_000.0,
    )


async def test_direct_routes_ios_to_apns_and_android_to_fcm(
    keys: tuple[ec.EllipticCurvePrivateKey, rsa.RSAPrivateKey],
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "oauth2.test":
            return httpx.Response(200, json={"access_token": "fcm-token", "expires_in": 3600})
        if request.url.host == "api.push.apple.com":
            if request.url.path.endswith("/ios-gone"):
                return httpx.Response(410, json={"reason": "Unregistered"})
            return httpx.Response(200)
        if json.loads(request.content)["message"]["token"] == "android-gone":
            return httpx.Response(
                404,
                json={
                    "error": {
                        "status": "NOT_FOUND",
                        "details": [{"errorCode": "UNREGISTERED"}],
                    }
                },
            )
        return httpx.Response(200, json={"name": "projects/stadtfest/messages/1"})

    sender = _direct(httpx.MockTransport(handler), keys)
    result = await sender.send(
        [
            _message("ios-ok", DevicePlatform.IOS),
            _message("ios-gone", DevicePlatform.IOS),
            _message("android-ok"),
            _message("android-gone"),
        ]
    )

    assert result.invalid_tokens == {"ios-gone", "android-gone"}
    apns = next(r for r in seen if r.url.path.endswith("/ios-ok"))
    assert apns.headers["apns-topic"] == "de.stadtfestfinder.app"
    assert apns.headers["apns-push-type"] == "alert"
    claims = jwt.decode(
        apns.headers["authorization"].removeprefix("bearer "),
        keys[0].public_key(),
        algorithms=["ES256"],
        options={"verify_iat": False},
    )
    assert claims["iss"] == "TEAM456"
    assert jwt.get_unverified_header(apns.headers["authorization"][7:])["kid"] == "KEY123"
    payload = json.loads(apns.content)
    assert payload["aps"] == {
        "alert": {"title": "Fest abgesagt", "body": "Eines deiner Lieblingsfeste fällt aus."},
        "sound": "default",
        "badge": 2,
    }
    assert payload["targetId"] == "e1"
    fcm = next(r for r in seen if r.url.host == "fcm.googleapis.com")
    assert fcm.url.path == "/v1/projects/stadtfest/messages:send"
    assert fcm.headers["authorization"] == "Bearer fcm-token"
    fcm_message = json.loads(fcm.content)["message"]
    assert fcm_message["data"]["type"] == "cancel"
    assert fcm_message["android"]["notification"] == {
        "channel_id": "default",
        "notification_count": 2,
    }
    # The OAuth token is fetched once and reused.
    assert sum(r.url.host == "oauth2.test" for r in seen) == 1


async def test_direct_keeps_tokens_on_payload_errors_and_fails_on_outages(
    keys: tuple[ec.EllipticCurvePrivateKey, rsa.RSAPrivateKey],
) -> None:
    def bad_payload(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.test":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        if request.url.host == "api.push.apple.com":
            return httpx.Response(400, json={"reason": "PayloadTooLarge"})
        return httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT"}})

    sender = _direct(httpx.MockTransport(bad_payload), keys)
    result = await sender.send([_message("ios", DevicePlatform.IOS), _message("android")])
    assert result.invalid_tokens == frozenset()

    outage = _direct(httpx.MockTransport(lambda _: httpx.Response(503)), keys)
    with pytest.raises(PushUnavailableError):
        await outage.send([_message("ios", DevicePlatform.IOS)])
