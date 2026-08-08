from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    FAILED_JOB_STATUS,
    JOB_STATUSES,
    JOB_TYPES,
    RUNNING_JOB_STATUS,
    SUCCEEDED_JOB_STATUS,
)
from app.db.models import Job, utc_now


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job_type: str, payload: dict[str, object]) -> Job:
        job = Job(type=job_type, payload=payload)
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: str) -> Job | None:
        return await self._session.get(Job, job_id)

    async def mark_running(self, job: Job) -> Job:
        job.status = RUNNING_JOB_STATUS
        job.started_at = utc_now()
        await self._session.flush()
        return job

    async def record_result(
        self,
        job: Job,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> Job:
        if error is None:
            job.status = SUCCEEDED_JOB_STATUS
            job.result = result
            job.error = None
        else:
            job.status = FAILED_JOB_STATUS
            job.result = None
            job.error = error
        job.finished_at = utc_now()
        await self._session.flush()
        return job

    async def list(
        self, job_status: str | None, limit: int, offset: int
    ) -> list[Job]:
        statement = select(Job)
        if job_status is not None:
            statement = statement.where(Job.status == job_status)
        statement = statement.order_by(Job.created_at.desc(), Job.id.asc())
        statement = statement.limit(limit).offset(offset)
        return list(await self._session.scalars(statement))

    async def count(self, job_status: str | None) -> int:
        statement = select(func.count(Job.id))
        if job_status is not None:
            statement = statement.where(Job.status == job_status)
        total = await self._session.scalar(statement)
        return total or 0

    async def stats(self) -> dict[str, Any]:
        status_counts = [
            func.count(case((Job.status == job_status, 1)))
            for job_status in JOB_STATUSES
        ]
        type_counts = [
            func.count(case((Job.type == job_type, 1))) for job_type in JOB_TYPES
        ]
        duration_seconds = func.unixepoch(
            Job.finished_at, "subsec"
        ) - func.unixepoch(Job.started_at, "subsec")
        terminal_duration = case(
            (
                and_(
                    Job.status.in_((SUCCEEDED_JOB_STATUS, FAILED_JOB_STATUS)),
                    Job.started_at.is_not(None),
                    Job.finished_at.is_not(None),
                ),
                duration_seconds,
            )
        )
        statement = select(
            *status_counts,
            *type_counts,
            func.count(Job.id),
            func.avg(terminal_duration),
        )
        values = (await self._session.execute(statement)).one()
        status_end = len(JOB_STATUSES)
        type_end = status_end + len(JOB_TYPES)
        average = values[type_end + 1]
        return {
            "jobs": {
                **dict(zip(JOB_STATUSES, values[:status_end], strict=True)),
                "total": values[type_end],
            },
            "by_type": dict(
                zip(JOB_TYPES, values[status_end:type_end], strict=True)
            ),
            "avg_duration_s": float(average) if average is not None else None,
        }

    async def delete(self, job: Job) -> None:
        await self._session.delete(job)
