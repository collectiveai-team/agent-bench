import asyncio
import logging

import pytest

from app.services import dispatcher
from app.services.dispatcher import InlineDispatcher, drain_dispatch_tasks


async def test_dispatch_failure_is_observed_not_swallowed(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def boom(job_id: str) -> None:
        raise RuntimeError("dispatch exploded")

    monkeypatch.setattr(dispatcher, "process_job", boom)

    with caplog.at_level(logging.ERROR, logger="app.services.dispatcher"):
        InlineDispatcher().enqueue("job-1")
        # Let the failing background task run and its done-callback fire.
        await asyncio.sleep(0.05)

    assert any(record.levelno == logging.ERROR for record in caplog.records)
    assert not dispatcher._background_tasks


async def test_drain_cancels_in_flight_dispatch_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()

    async def never_ends(job_id: str) -> None:
        started.set()
        await asyncio.sleep(3600)

    monkeypatch.setattr(dispatcher, "process_job", never_ends)

    InlineDispatcher().enqueue("job-2")
    await started.wait()
    task = next(iter(dispatcher._background_tasks))

    await drain_dispatch_tasks()

    assert task.cancelled()
    await asyncio.sleep(0)
    assert not dispatcher._background_tasks
