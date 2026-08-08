import asyncio
from datetime import UTC, datetime
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import (
    DEFAULT_EVENT_QUEUE_SIZE,
    DEFAULT_JOB_STATUS,
    FAILED_JOB_STATUS,
    JOB_CREATED_EVENT,
    JOB_FAILED_EVENT,
    JOB_STARTED_EVENT,
    JOB_STATUS_POLL_INTERVAL_S,
    JOB_SUCCEEDED_EVENT,
    RUNNING_JOB_STATUS,
    SUCCEEDED_JOB_STATUS,
    JobEventName,
)
from app.db.models import Job

Event = dict[str, Any]


class JobStateEvent(TypedDict):
    event: JobEventName
    job_id: str
    status: str


_STATUS_EVENT_NAMES: dict[str, JobEventName] = {
    DEFAULT_JOB_STATUS: JOB_CREATED_EVENT,
    RUNNING_JOB_STATUS: JOB_STARTED_EVENT,
    SUCCEEDED_JOB_STATUS: JOB_SUCCEEDED_EVENT,
    FAILED_JOB_STATUS: JOB_FAILED_EVENT,
}


class EventBus:
    def __init__(self, queue_size: int = DEFAULT_EVENT_QUEUE_SIZE) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be positive")
        self._queue_size = queue_size
        self._subscribers: set[asyncio.Queue[Event]] = set()

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: Event) -> None:
        for queue in tuple(self._subscribers):
            try:
                if queue.full():
                    queue.get_nowait()
                queue.put_nowait(event.copy())
            except Exception:
                continue

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


def create_job_event(
    event_name: JobEventName, job_id: str, job_status: str
) -> dict[str, str]:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {
        "event": event_name,
        "job_id": job_id,
        "status": job_status,
        "ts": timestamp,
    }


def diff_job_states(
    previous: dict[str, str], current: dict[str, str]
) -> list[JobStateEvent]:
    events: list[JobStateEvent] = []
    for job_id, job_status in current.items():
        if previous.get(job_id) == job_status:
            continue
        event_name = _STATUS_EVENT_NAMES.get(job_status)
        if event_name is not None:
            events.append(
                {"event": event_name, "job_id": job_id, "status": job_status}
            )
    return events


async def _read_job_states(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, str]:
    async with session_factory() as session:
        rows = await session.execute(
            select(Job.id, Job.status).order_by(Job.id.asc())
        )
        return {job_id: job_status for job_id, job_status in rows.all()}


async def poll_job_states(
    session_factory: async_sessionmaker[AsyncSession], bus: EventBus
) -> None:
    # Seed the baseline from whatever is already persisted so pre-existing jobs
    # are not mistaken for fresh state changes on the first tick.
    previous = await _read_job_states(session_factory)
    while True:
        await asyncio.sleep(JOB_STATUS_POLL_INTERVAL_S)
        current = await _read_job_states(session_factory)
        for event in diff_job_states(previous, current):
            # job.created is emitted once, on POST, by JobService. The poller only
            # reports the out-of-process worker's state transitions, so it must not
            # re-publish creation for a newly observed pending row.
            if event["event"] == JOB_CREATED_EVENT:
                continue
            bus.publish(
                create_job_event(event["event"], event["job_id"], event["status"])
            )
        previous = current


_event_bus = EventBus()


def get_event_bus() -> EventBus:
    return _event_bus
