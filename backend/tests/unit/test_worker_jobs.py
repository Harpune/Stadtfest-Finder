from types import SimpleNamespace
from typing import Any

import pytest
from arq import Retry

from stadtfest.adapters.inbound.worker.jobs import IDP_DELETION_MAX_TRIES, delete_idp_user
from stadtfest.application.identity.use_cases import DeleteIdpUser
from tests.fakes import FakeIdpAdmin


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
