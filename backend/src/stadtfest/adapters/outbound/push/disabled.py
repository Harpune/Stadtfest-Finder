"""`PUSH_PROVIDER=disabled`: no pushes (default for local development and tests)."""

from __future__ import annotations

from collections.abc import Sequence

from stadtfest.application.notifications.ports import PushMessage, PushProvider, PushResult


class DisabledPushSender:
    """Sends nothing; notifications still appear in the list."""

    provider = PushProvider.DISABLED

    async def send(self, messages: Sequence[PushMessage]) -> PushResult:
        """Drop the messages."""
        return PushResult()

    async def check_receipts(self, receipts: dict[str, str]) -> frozenset[str]:
        """Nothing to check."""
        return frozenset()
