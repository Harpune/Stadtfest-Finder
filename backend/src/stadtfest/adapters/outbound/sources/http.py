"""Reachability check of source pages (R10-US3 step 6) with SSRF protection.

The URLs come from web search results, so the worker never requests addresses in private,
loopback, link-local or otherwise reserved networks.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

TIMEOUT_SECONDS = 5.0
_USER_AGENT = "stadtfest-finder-source-check/0.1"


async def is_public_host(host: str) -> bool:
    """True if every address of the host is public."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return False
    addresses = {info[4][0] for info in infos}
    if not addresses:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(str(address).split("%")[0])
        if not ip.is_global:
            return False
    return True


class HttpSourceChecker:
    """Implements `SourceChecker` with HEAD (GET as fallback), status < 400, 5 s timeout."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Create the checker.

        Args:
            client: HTTP client without cookies; redirects are followed manually.
        """
        self._client = client

    async def reachable(self, url: str) -> bool:
        """True if the page answers below status 400."""
        current = url
        for _ in range(4):  # the URL and up to three redirects, each host checked
            parts = urlsplit(current)
            if parts.scheme not in {"http", "https"} or not parts.hostname:
                return False
            if not await is_public_host(parts.hostname):
                return False
            try:
                response = await self._client.head(current)
                if response.status_code in {403, 405}:  # some servers refuse HEAD
                    response = await self._client.get(current)
            except httpx.HTTPError:
                return False
            if response.is_redirect and "location" in response.headers:
                current = str(response.url.join(response.headers["location"]))
                continue
            return response.status_code < 400
        return False


class AllowAllSourceChecker:
    """Local development with the fake search: its example pages do not exist."""

    async def reachable(self, url: str) -> bool:
        """Always true."""
        return True


def create_source_client() -> httpx.AsyncClient:
    """HTTP client for source checks (no redirects followed automatically)."""
    return httpx.AsyncClient(
        timeout=TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"User-Agent": _USER_AGENT},
    )
