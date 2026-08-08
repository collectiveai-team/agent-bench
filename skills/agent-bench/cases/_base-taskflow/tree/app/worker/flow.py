from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from prefect import flow, task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    JOB_FAILED_EVENT,
    JOB_STARTED_EVENT,
    JOB_SUCCEEDED_EVENT,
    PROCESS_JOB_FLOW_NAME,
    REVERSE_JOB_TYPE,
    SUMMARY_STATS_JOB_TYPE,
    WORD_COUNT_JOB_TYPE,
    get_settings,
)
from app.db.models import Job
from app.db.session import create_database
from app.events import create_job_event, get_event_bus
from app.repositories.jobs import JobRepository


@asynccontextmanager
async def _worker_session() -> AsyncIterator[AsyncSession]:
    engine, session_factory = create_database(get_settings().db_path)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


async def _get_job(repository: JobRepository, job_id: str) -> Job:
    job = await repository.get(job_id)
    if job is None:
        raise ValueError("job not found")
    return job


@task
async def mark_running(job_id: str) -> tuple[str, dict[str, Any]]:
    async with _worker_session() as session:
        repository = JobRepository(session)
        job = await _get_job(repository, job_id)
        await repository.mark_running(job)
        await session.commit()
        get_event_bus().publish(
            create_job_event(JOB_STARTED_EVENT, job.id, job.status)
        )
        return job.type, job.payload


@task(retries=1)
async def execute(job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("payload.text must be a non-empty string")

    words = text.split()
    if job_type == WORD_COUNT_JOB_TYPE:
        return {"words": len(words), "chars": len(text)}
    if job_type == REVERSE_JOB_TYPE:
        return {"text": text[::-1]}
    if job_type == SUMMARY_STATS_JOB_TYPE:
        return {
            "lines": len(text.splitlines()),
            "words": len(words),
            "unique_words": len({word.casefold() for word in words}),
        }
    raise ValueError(f"unknown job type: {job_type}")


@task
async def finalize(
    job_id: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    async with _worker_session() as session:
        repository = JobRepository(session)
        job = await _get_job(repository, job_id)
        await repository.record_result(job, result=result, error=error)
        await session.commit()
        event_name = JOB_SUCCEEDED_EVENT if error is None else JOB_FAILED_EVENT
        get_event_bus().publish(create_job_event(event_name, job.id, job.status))


@flow(name=PROCESS_JOB_FLOW_NAME, log_prints=True)
async def process_job(job_id: str) -> None:
    try:
        job_type, payload = await mark_running(job_id)
        result = await execute(job_type, payload)
    except Exception as exc:
        error = str(exc).strip() or type(exc).__name__
        try:
            await finalize(job_id, error=error)
        except Exception:
            return
        return

    try:
        await finalize(job_id, result=result)
    except Exception:
        return
