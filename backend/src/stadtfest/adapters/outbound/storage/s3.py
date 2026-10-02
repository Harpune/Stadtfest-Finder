"""S3 object storage via aiobotocore (SeaweedFS locally, an EU S3 in production, ADR 0007)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aiohttp
from aiobotocore.config import AioConfig
from aiobotocore.session import get_session
from botocore.exceptions import BotoCoreError, ClientError

from stadtfest.application.moderation.image_ports import (
    PresignedUpload,
    StorageUnavailableError,
)

if TYPE_CHECKING:  # stubs are a dev dependency
    from types_aiobotocore_s3 import S3Client

# Variant keys never change (they contain the image ID), so clients may cache them for a year.
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
_DELETE_BATCH = 1000
_NOT_FOUND = frozenset({"404", "NoSuchKey", "NotFound"})
_STORAGE_ERRORS = (BotoCoreError, aiohttp.ClientError, asyncio.TimeoutError)


@dataclass(frozen=True, slots=True)
class S3Config:
    """Connection settings of the bucket.

    Attributes:
        endpoint_url: S3 endpoint the backend talks to, e.g. `http://seaweedfs:8333`.
        presign_endpoint_url: Endpoint the app uploads to (signed URLs); defaults to
            `endpoint_url`. Differs when the backend reaches the storage internally.
        bucket: Bucket name.
        region: Region name used for signing.
        access_key_id: Access key.
        secret_access_key: Secret key.
        timeout_seconds: Connect and read timeout.
    """

    endpoint_url: str
    bucket: str
    region: str
    access_key_id: str
    secret_access_key: str
    presign_endpoint_url: str | None = None
    timeout_seconds: float = 10.0


class S3ObjectStorage:
    """Implements `ObjectStorage` against an S3-compatible service."""

    def __init__(self, config: S3Config) -> None:
        """Create the adapter; clients are opened on first use and closed by `aclose`."""
        self._config = config
        self._stack = AsyncExitStack()
        self._client: S3Client | None = None
        self._presign_client: S3Client | None = None
        self._lock = asyncio.Lock()

    async def _clients(self) -> tuple[S3Client, S3Client]:
        async with self._lock:
            if self._client is None or self._presign_client is None:
                presign_url = self._config.presign_endpoint_url or self._config.endpoint_url
                self._client = await self._open(self._config.endpoint_url)
                self._presign_client = await self._open(presign_url)
            return self._client, self._presign_client

    async def _open(self, endpoint_url: str) -> S3Client:
        config = AioConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=self._config.timeout_seconds,
            read_timeout=self._config.timeout_seconds,
            retries={"max_attempts": 2},
        )
        client: S3Client = await self._stack.enter_async_context(
            get_session().create_client(
                "s3",
                endpoint_url=endpoint_url,
                region_name=self._config.region,
                aws_access_key_id=self._config.access_key_id,
                aws_secret_access_key=self._config.secret_access_key,
                config=config,
            )
        )
        return client

    async def aclose(self) -> None:
        """Close the HTTP sessions."""
        await self._stack.aclose()
        self._client = self._presign_client = None

    async def presign_put(
        self, key: str, content_type: str, size_bytes: int, expires_in_seconds: int
    ) -> PresignedUpload:
        """Sign a PUT of exactly this type and size (both are signed headers)."""
        _, presign = await self._clients()
        try:
            url = await presign.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._config.bucket,
                    "Key": key,
                    "ContentType": content_type,
                    "ContentLength": size_bytes,
                },
                ExpiresIn=expires_in_seconds,
            )
        except _STORAGE_ERRORS as exc:
            raise StorageUnavailableError from exc
        return PresignedUpload(url, {"Content-Type": content_type})

    async def read(self, key: str) -> bytes | None:
        """Return the object's content, or None if it does not exist."""
        client, _ = await self._clients()
        try:
            response = await client.get_object(Bucket=self._config.bucket, Key=key)
            async with response["Body"] as stream:
                return await stream.read()
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND:
                return None
            raise StorageUnavailableError from exc
        except _STORAGE_ERRORS as exc:
            raise StorageUnavailableError from exc

    async def exists(self, key: str) -> bool:
        """Whether the object exists."""
        client, _ = await self._clients()
        try:
            await client.head_object(Bucket=self._config.bucket, Key=key)
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND:
                return False
            raise StorageUnavailableError from exc
        except _STORAGE_ERRORS as exc:
            raise StorageUnavailableError from exc
        return True

    async def write(self, key: str, data: bytes, content_type: str) -> None:
        """Store an immutable public object."""
        client, _ = await self._clients()
        try:
            await client.put_object(
                Bucket=self._config.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl=IMMUTABLE_CACHE_CONTROL,
            )
        except (ClientError, *_STORAGE_ERRORS) as exc:
            raise StorageUnavailableError from exc

    async def delete(self, keys: Sequence[str]) -> None:
        """Delete objects in batches; unknown keys are ignored by S3."""
        if not keys:
            return
        client, _ = await self._clients()
        try:
            for start in range(0, len(keys), _DELETE_BATCH):
                batch = keys[start : start + _DELETE_BATCH]
                await client.delete_objects(
                    Bucket=self._config.bucket,
                    Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
                )
        except (ClientError, *_STORAGE_ERRORS) as exc:
            raise StorageUnavailableError from exc

    async def ensure_bucket(self) -> None:
        """Create the bucket if it is missing (local development and tests).

        Raises:
            StorageUnavailableError: If the storage cannot be reached.
        """
        client, _ = await self._clients()
        try:
            await client.head_bucket(Bucket=self._config.bucket)
        except ClientError as exc:
            if _error_code(exc) not in _NOT_FOUND | {"NoSuchBucket"}:
                raise StorageUnavailableError from exc
            try:
                await client.create_bucket(Bucket=self._config.bucket)
            except (ClientError, *_STORAGE_ERRORS) as create_exc:
                raise StorageUnavailableError from create_exc
        except _STORAGE_ERRORS as exc:
            raise StorageUnavailableError from exc


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
