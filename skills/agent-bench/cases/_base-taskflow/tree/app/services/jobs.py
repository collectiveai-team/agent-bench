from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    DEFAULT_JOB_LIMIT,
    DEFAULT_JOB_OFFSET,
    JOB_CREATED_EVENT,
    JOB_STATUSES,
    MAX_JOB_LIMIT,
    MIN_JOB_LIMIT,
    PREFECT_WORKER_MODE,
    RUNNING_JOB_STATUS,
    Settings,
)
from app.db.models import Job
from app.events import EventBus, create_job_event, get_event_bus
from app.repositories.jobs import JobRepository
from app.schemas import JobCreate
from app.services.dispatcher import InlineDispatcher, JobDispatcher, PrefectDispatcher


class JobNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("job not found")


class JobRunningError(Exception):
    def __init__(self) -> None:
        super().__init__("job is running")


class InvalidJobListQueryError(Exception):
    pass


class JobService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        dispatcher: JobDispatcher | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._session = session
        self._repository = JobRepository(session)
        self._event_bus = event_bus or get_event_bus()
        if dispatcher is not None:
            self._dispatcher = dispatcher
        elif settings.worker_mode == PREFECT_WORKER_MODE:
            self._dispatcher = PrefectDispatcher()
        else:
            self._dispatcher = InlineDispatcher()

    async def create(self, job_create: JobCreate) -> Job:
        job = await self._repository.create(job_create.type, job_create.payload)
        await self._session.commit()
        self._event_bus.publish(
            create_job_event(JOB_CREATED_EVENT, job.id, job.status)
        )
        self._dispatcher.enqueue(job.id)
        return job

    async def get(self, job_id: str) -> Job:
        job = await self._repository.get(job_id)
        if job is None:
            raise JobNotFoundError
        return job

    async def list(
        self,
        job_status: str | None = None,
        limit: int = DEFAULT_JOB_LIMIT,
        offset: int = DEFAULT_JOB_OFFSET,
    ) -> tuple[list[Job], int]:
        if job_status is not None and job_status not in JOB_STATUSES:
            raise InvalidJobListQueryError("invalid status")
        if not MIN_JOB_LIMIT <= limit <= MAX_JOB_LIMIT:
            raise InvalidJobListQueryError(
                f"limit must be between {MIN_JOB_LIMIT} and {MAX_JOB_LIMIT}"
            )
        if offset < DEFAULT_JOB_OFFSET:
            raise InvalidJobListQueryError("offset must be non-negative")

        jobs = await self._repository.list(job_status, limit, offset)
        total = await self._repository.count(job_status)
        return jobs, total

    async def stats(self) -> dict[str, object]:
        return await self._repository.stats()

    async def delete(self, job_id: str) -> None:
        job = await self.get(job_id)
        if job.status == RUNNING_JOB_STATUS:
            raise JobRunningError
        await self._repository.delete(job)
        await self._session.commit()
