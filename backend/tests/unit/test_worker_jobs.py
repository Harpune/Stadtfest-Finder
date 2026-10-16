from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from arq import Retry

from stadtfest.adapters.inbound.worker.jobs import (
    IDP_DELETION_MAX_TRIES,
    PUSH_MAX_TRIES,
    check_push_receipts,
    delete_idp_user,
    push_notifications,
)
from stadtfest.application.identity.use_cases import DeleteIdpUser
from stadtfest.application.notifications.use_cases import CheckPushReceipts, PushNotifications
from stadtfest.bootstrap.settings import Environment, GeocodingProvider, Settings
from tests.fakes import (
    FakeDeviceStore,
    FakeIdpAdmin,
    FakeNotificationStore,
    FakePushJobs,
    FakePushSender,
    FakeSettingsStore,
)


def _ctx(idp: FakeIdpAdmin, job_try: int = 1) -> dict[str, Any]:
    container = SimpleNamespace(delete_idp_user=DeleteIdpUser(idp))
    return {"container": container, "job_try": job_try, "job_id": "delete_idp_user:sub-1"}


async def test_delete_idp_user_job_deletes_user() -> None:
    idp = FakeIdpAdmin()
    await delete_idp_user(_ctx(idp), "sub-1")
    assert idp.deleted == ["sub-1"]


async def test_delete_idp_user_job_retries_with_backoff() -> None:
    with pytest.raises(Retry) as retry:
        await delete_idp_user(_ctx(FakeIdpAdmin(unavailable=True), job_try=3), "sub-1")
    assert retry.value.defer_score == 240_000


async def test_delete_idp_user_job_gives_up_after_max_tries(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ctx = _ctx(FakeIdpAdmin(unavailable=True), job_try=IDP_DELETION_MAX_TRIES)
    await delete_idp_user(ctx, "sub-1")
    assert "idp_deletion_failed" in caplog.text


def _push_ctx(sender: FakePushSender, job_try: int = 1) -> dict[str, Any]:
    store, devices = FakeNotificationStore(), FakeDeviceStore()
    container = SimpleNamespace(
        push_notifications=PushNotifications(
            store, FakeSettingsStore(), devices, sender, FakePushJobs()
        ),
        check_push_receipts=CheckPushReceipts(sender, devices),
    )
    return {"container": container, "job_try": job_try, "job_id": "push_notifications:n1"}


async def test_push_job_retries_while_the_service_is_down(
    caplog: pytest.LogCaptureFixture,
) -> None:
    down = FakePushSender(unavailable=True)
    with pytest.raises(Retry) as retry:
        await check_push_receipts(_push_ctx(down, job_try=2), {"t": "x"})
    assert retry.value.defer_score == 60_000
    assert await check_push_receipts(_push_ctx(down, job_try=PUSH_MAX_TRIES), {"t": "x"}) == 0
    assert "push_failed" in caplog.text
    assert await push_notifications(_push_ctx(FakePushSender()), [str(uuid4())]) == 0


def test_worker_entry_point_rejects_unknown_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    from stadtfest.bootstrap.worker import main

    assert main(["--bogus"]) == 2
    assert "--check" in capsys.readouterr().err


async def test_worker_shutdown_after_failed_startup_keeps_the_original_error() -> None:
    from stadtfest.bootstrap.worker import build_worker_settings
    from tests.settings_values import TEST_STORAGE

    settings = Settings(
        env=Environment.TEST,
        geocoding_provider=GeocodingProvider.FAKE,
        database_url="postgresql+asyncpg://u:p@127.0.0.1:9/db",
        redis_url="redis://127.0.0.1:9/0",
        **TEST_STORAGE,  # type: ignore[arg-type]
    )
    worker_settings = build_worker_settings(settings)

    await worker_settings.on_shutdown({})  # type: ignore[attr-defined]
