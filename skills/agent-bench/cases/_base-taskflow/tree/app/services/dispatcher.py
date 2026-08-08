import asyncio
import logging
from collections.abc import Coroutine
from contextlib import suppress
from typing import Any, Protocol

from prefect.deployments import run_deployment

from app.core.config import PROCESS_JOB_DEPLOYMENT_FULL_NAME
from app.worker.flow import process_job

_logger = logging.getLogger(__name__)

# Shared registry of in-flight dispatch tasks. asyncio.create_task returns a task
# whose exceptions would otherwise be swallowed (POST already returned 201) and
# which would leak on shutdown; tracking lets us observe failures and drain them.
_background_tasks: set[asyncio.Task[None]] = set()


def _spawn(coro: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_on_task_done)
    return task


def _on_task_done(task: asyncio.Task[None]) -> None:
    _background_tasks.discard(task)
    if task.cancelled():
        return
    exception = task.exception()
    if exception is not None:
        _logger.error("background job dispatch failed", exc_info=exception)


async def drain_dispatch_tasks() -> None:
    tasks = tuple(_background_tasks)
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError, Exception):
            await task


class JobDispatcher(Protocol):
    def enqueue(self, job_id: str) -> None: ...


class InlineDispatcher:
    def enqueue(self, job_id: str) -> None:
        _spawn(process_job(job_id))


async def _submit_to_prefect(job_id: str) -> None:
    await run_deployment(
        PROCESS_JOB_DEPLOYMENT_FULL_NAME,
        parameters={"job_id": job_id},
        timeout=0,
    )


class PrefectDispatcher:
    def enqueue(self, job_id: str) -> None:
        _spawn(_submit_to_prefect(job_id))
