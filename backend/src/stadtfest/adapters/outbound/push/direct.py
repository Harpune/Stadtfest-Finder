"""`PUSH_PROVIDER=direct`: the backend sends to APNs (iOS) and FCM (Android) itself.

One processor fewer than with Expo (ADR 0016). APNs only speaks HTTP/2, so the client
needs `http2=True`. Both services authenticate with short-lived JWTs signed by keys from
files (`APNS_KEY_PATH`, `FCM_CREDENTIALS_PATH`); tokens are cached and renewed early.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx
import jwt

from stadtfest.application.notifications.ports import (
    DevicePlatform,
    PushMessage,
    PushProvider,
    PushResult,
    PushUnavailableError,
)

APNS_HOST = "https://api.push.apple.com"
APNS_SANDBOX_HOST = "https://api.sandbox.push.apple.com"
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
# Apple accepts provider tokens for an hour and rejects renewals more often than every 20 min.
APNS_TOKEN_SECONDS = 50 * 60
MAX_PARALLEL = 10
# Android channel created by the app (`setNotificationChannelAsync("default")`).
ANDROID_CHANNEL = "default"
_APNS_INVALID = frozenset({"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"})
_FCM_INVALID = frozenset({"UNREGISTERED"})

Clock = Callable[[], float]
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ApnsConfig:
    """APNs token authentication (`.p8` key from the Apple developer account)."""

    key_id: str
    team_id: str
    private_key: str
    topic: str
    sandbox: bool = False

    @classmethod
    def from_file(
        cls, key_id: str, team_id: str, key_path: Path, topic: str, *, sandbox: bool
    ) -> ApnsConfig:
        """Read the key file."""
        return cls(key_id, team_id, key_path.read_text(encoding="utf-8"), topic, sandbox)


@dataclass(frozen=True, slots=True)
class FcmConfig:
    """FCM HTTP v1 with a service account (JSON key from the Firebase console)."""

    project_id: str
    client_email: str
    private_key: str
    token_uri: str

    @classmethod
    def from_file(cls, project_id: str, credentials_path: Path) -> FcmConfig:
        """Read the service account file."""
        data = json.loads(credentials_path.read_text(encoding="utf-8"))
        return cls(
            project_id,
            data["client_email"],
            data["private_key"],
            data.get("token_uri", "https://oauth2.googleapis.com/token"),
        )


class DirectPushSender:
    """Implements `PushSender` with APNs and FCM; per-device errors never stop a batch."""

    provider = PushProvider.DIRECT

    def __init__(
        self,
        client: httpx.AsyncClient,
        apns: ApnsConfig,
        fcm: FcmConfig,
        clock: Clock = time.time,
    ) -> None:
        """Create the sender.

        Args:
            client: HTTP client with HTTP/2 enabled (APNs requires it).
            apns: APNs credentials.
            fcm: FCM credentials.
            clock: Unix time, injectable for tests.
        """
        self._client = client
        self._apns = apns
        self._fcm = fcm
        self._clock = clock
        self._apns_token: tuple[str, float] | None = None
        self._fcm_token: tuple[str, float] | None = None
        self._fcm_lock = asyncio.Lock()
        self._limit = asyncio.Semaphore(MAX_PARALLEL)

    async def send(self, messages: Sequence[PushMessage]) -> PushResult:
        """Send each message to its platform's service, at most 10 at once."""
        results = await asyncio.gather(*(self._send_one(message) for message in messages))
        return PushResult(frozenset(token for token in results if token is not None))

    async def check_receipts(self, receipts: dict[str, str]) -> frozenset[str]:
        """APNs and FCM report errors immediately; there are no receipts."""
        return frozenset()

    async def _send_one(self, message: PushMessage) -> str | None:
        """Send one message; returns the token if the service rejected it for good."""
        async with self._limit:
            if message.platform is DevicePlatform.IOS:
                return await self._apns_send(message)
            return await self._fcm_send(message)

    # --- APNs ----------------------------------------------------------------------------

    def _apns_jwt(self) -> str:
        now = self._clock()
        if self._apns_token is None or now - self._apns_token[1] > APNS_TOKEN_SECONDS:
            token = jwt.encode(
                {"iss": self._apns.team_id, "iat": int(now)},
                self._apns.private_key,
                algorithm="ES256",
                headers={"kid": self._apns.key_id},
            )
            self._apns_token = (token, now)
        return self._apns_token[0]

    async def _apns_send(self, message: PushMessage) -> str | None:
        host = APNS_SANDBOX_HOST if self._apns.sandbox else APNS_HOST
        aps: dict[str, object] = {
            "alert": {"title": message.title, "body": message.body},
            "sound": "default",
        }
        if message.badge is not None:
            aps["badge"] = message.badge
        response = await self._post(
            f"{host}/3/device/{message.token}",
            json={"aps": aps, **message.data},
            headers={
                "authorization": f"bearer {self._apns_jwt()}",
                "apns-topic": self._apns.topic,
                "apns-push-type": "alert",
                "apns-priority": "10",
            },
        )
        if response.status_code == 200:
            return None
        reason = _json_field(response, "reason")
        if response.status_code == 410 or reason in _APNS_INVALID:
            return message.token
        if response.status_code == 400:
            # A problem of this message (e.g. payload too large): retrying will not help.
            logger.warning("apns_rejected", extra={"reason": reason})
            return None
        raise PushUnavailableError(f"apns {response.status_code} {reason}")

    # --- FCM -----------------------------------------------------------------------------

    async def _fcm_access_token(self) -> str:
        async with self._fcm_lock:
            now = self._clock()
            if self._fcm_token is not None and now < self._fcm_token[1]:
                return self._fcm_token[0]
            assertion = jwt.encode(
                {
                    "iss": self._fcm.client_email,
                    "scope": FCM_SCOPE,
                    "aud": self._fcm.token_uri,
                    "iat": int(now),
                    "exp": int(now) + 3600,
                },
                self._fcm.private_key,
                algorithm="RS256",
            )
            response = await self._post(
                self._fcm.token_uri,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
            )
            token = _json_field(response, "access_token")
            if response.status_code != 200 or token is None:
                raise PushUnavailableError(f"fcm auth {response.status_code}")
            expires_in = _json_number(response, "expires_in") or 3600
            self._fcm_token = (token, now + expires_in - 60)
            return token

    async def _fcm_send(self, message: PushMessage) -> str | None:
        notification: dict[str, object] = {"channel_id": ANDROID_CHANNEL}
        if message.badge is not None:
            notification["notification_count"] = message.badge
        android: dict[str, object] = {"priority": "HIGH", "notification": notification}
        response = await self._post(
            f"https://fcm.googleapis.com/v1/projects/{self._fcm.project_id}/messages:send",
            json={
                "message": {
                    "token": message.token,
                    "notification": {"title": message.title, "body": message.body},
                    "data": message.data,
                    "android": android,
                }
            },
            headers={"authorization": f"Bearer {await self._fcm_access_token()}"},
        )
        if response.status_code == 200:
            return None
        code = _fcm_error_code(response)
        if code in _FCM_INVALID or response.status_code == 404:
            return message.token
        if response.status_code == 400:
            # INVALID_ARGUMENT can mean a bad token or a bad payload; keep the token.
            logger.warning("fcm_rejected", extra={"reason": code})
            return None
        raise PushUnavailableError(f"fcm {response.status_code}")

    async def _post(self, url: str, **kwargs: object) -> httpx.Response:
        try:
            return await self._client.post(url, **kwargs)  # type: ignore[arg-type]
        except httpx.HTTPError as error:
            raise PushUnavailableError(type(error).__name__) from None


def _json(response: httpx.Response) -> dict[str, object]:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _json_field(response: httpx.Response, key: str) -> str | None:
    value = _json(response).get(key)
    return value if isinstance(value, str) else None


def _json_number(response: httpx.Response, key: str) -> int | None:
    value = _json(response).get(key)
    return value if isinstance(value, int) else None


def _fcm_error_code(response: httpx.Response) -> str | None:
    """`errorCode` from the error details, falling back to the status (FCM HTTP v1)."""
    error = _json(response).get("error")
    if not isinstance(error, dict):
        return None
    details = error.get("details")
    if isinstance(details, list):
        for detail in details:
            if isinstance(detail, dict) and isinstance(detail.get("errorCode"), str):
                return str(detail["errorCode"])
    status = error.get("status")
    return status if isinstance(status, str) else None
