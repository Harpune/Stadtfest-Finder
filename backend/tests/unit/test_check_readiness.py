import asyncio

from stadtfest.application.health.check_readiness import CheckReadiness


class FakeProbe:
    def __init__(self, name: str, *, available: bool = True, delay: float = 0.0) -> None:
        self.name = name
        self._available = available
        self._delay = delay

    async def is_available(self) -> bool:
        await asyncio.sleep(self._delay)
        if not self._available:
            raise ConnectionError("down")
        return True


async def test_ready_when_all_probes_succeed() -> None:
    readiness = await CheckReadiness([FakeProbe("database"), FakeProbe("redis")])()
    assert readiness.ready
    assert readiness.checks == {"database": True, "redis": True}


async def test_failing_probe_marks_unready() -> None:
    readiness = await CheckReadiness([FakeProbe("database"), FakeProbe("redis", available=False)])()
    assert not readiness.ready
    assert readiness.checks["redis"] is False


async def test_slow_probe_times_out() -> None:
    use_case = CheckReadiness([FakeProbe("database", delay=0.5)], timeout_seconds=0.05)
    readiness = await use_case()
    assert readiness.checks == {"database": False}
