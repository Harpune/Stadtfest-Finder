"""Storage settings for tests that build `Settings` directly (the storage is never reached)."""

from __future__ import annotations

TEST_STORAGE: dict[str, str] = {
    "s3_endpoint_url": "http://127.0.0.1:9",
    "s3_public_base_url": "http://127.0.0.1:9/stadtfest-images",
    "s3_access_key_id": "test",
    "s3_secret_access_key": "test",
}
