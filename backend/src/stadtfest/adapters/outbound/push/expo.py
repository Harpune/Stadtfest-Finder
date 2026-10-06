"""`PUSH_PROVIDER=expo`: Expo Push Service, which forwards to APNs and FCM (ADR 0016).

Up to 100 messages per request; tokens rejected with `DeviceNotRegistered` are invalid,
either directly in the ticket or later in the receipt.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import batched

import httpx

from stadtfest.application.notifications.ports import (
    PushMessage,
    PushProvider,
    PushResult,
    PushUnavailableError,
)

SEND_URL = "https://exp.host/--/api/v2/push/send"
RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"
SEND_BATCH = 100
RECEIPT_BATCH = 1000
_INVALID = "DeviceNotRegistered"
ANDROID_CHANNEL = "default"


class ExpoPushSender:
    """Implements `PushSender` with the Expo push API."""

    provider = PushProvider.EXPO

    def __init__(self, client: httpx.AsyncClient, access_token: str | None) -> None:
        """Create the sender.

        Args:
            client: HTTP client.
            access_token: `EXPO_ACCESS_TOKEN` (needed if "enhanced security" is on).
        """
        self._client = client
        self._headers = {"accept": "application/json", "accept-encoding": "gzip, deflate"}
        if access_token:
            self._headers["authorization"] = f"Bearer {access_token}"

    async def send(self, messages: Sequence[PushMessage]) -> PushResult:
        """Send in batches of 100."""
        invalid: set[str] = set()
        receipts: dict[str, str] = {}
        for batch in batched(messages, SEND_BATCH):
            body = [_expo_message(message) for message in batch]
            tickets = await self._post(SEND_URL, body)
            if not isinstance(tickets, list) or len(tickets) != len(batch):
                raise PushUnavailableError("unexpected response")
            for message, ticket in zip(batch, tickets, strict=True):
                if not isinstance(ticket, dict):
                    continue
                if ticket.get("status") == "ok" and isinstance(ticket.get("id"), str):
                    receipts[ticket["id"]] = message.token
                elif _error(ticket) == _INVALID:
                    invalid.add(message.token)
        return PushResult(frozenset(invalid), receipts)

    async def check_receipts(self, receipts: dict[str, str]) -> frozenset[str]:
        """Tokens whose receipt says `DeviceNotRegistered`; missing receipts are ignored."""
        invalid: set[str] = set()
        for batch in batched(receipts, RECEIPT_BATCH):
            data = await self._post(RECEIPTS_URL, {"ids": list(batch)})
            if not isinstance(data, dict):
                raise PushUnavailableError("unexpected response")
            for ticket_id, receipt in data.items():
                if isinstance(receipt, dict) and _error(receipt) == _INVALID:
                    invalid.add(receipts[ticket_id])
        return frozenset(invalid)

    async def _post(self, url: str, body: object) -> object:
        try:
            response = await self._client.post(url, json=body, headers=self._headers)
        except httpx.HTTPError as error:
            raise PushUnavailableError(type(error).__name__) from None
        if response.status_code != 200:
            raise PushUnavailableError(f"status {response.status_code}")
        try:
            payload = response.json()
        except ValueError:
            raise PushUnavailableError("invalid json") from None
        if not isinstance(payload, dict) or "data" not in payload:
            raise PushUnavailableError("request error")
        return payload["data"]


def _expo_message(message: PushMessage) -> dict[str, object]:
    body: dict[str, object] = {
        "to": message.token,
        "title": message.title,
        "body": message.body,
        "data": message.data,
        "sound": "default",
        "priority": "high",
        # Android channel created by the app (`setNotificationChannelAsync("default")`).
        "channelId": ANDROID_CHANNEL,
    }
    if message.badge is not None:
        body["badge"] = message.badge
    return body


def _error(ticket: dict[str, object]) -> str | None:
    details = ticket.get("details")
    if ticket.get("status") == "error" and isinstance(details, dict):
        error = details.get("error")
        return error if isinstance(error, str) else None
    return None
