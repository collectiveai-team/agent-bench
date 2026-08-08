import asyncio
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import (
    DEFAULT_JOB_STATUS,
    FAILED_JOB_STATUS,
    JOB_CREATED_EVENT,
    JOB_FAILED_EVENT,
    JOB_STARTED_EVENT,
    JOB_SUCCEEDED_EVENT,
    PREFECT_WORKER_MODE,
    RUNNING_JOB_STATUS,
    SUCCEEDED_JOB_STATUS,
    WS_CONNECTED_EVENT,
    WORD_COUNT_JOB_TYPE,
    Settings,
    get_settings,
)
from app.db.models import Job
from app.db.session import create_database, init_db
from app.events import (
    EventBus,
    Event,
    create_job_event,
    diff_job_states,
    get_event_bus,
    poll_job_states,
)
from app.main import create_app
from app.routes.jobs import get_job_service
from app.worker.flow import process_job


def test_event_bus_fans_out_and_tracks_subscribers() -> None:
    bus = EventBus(queue_size=2)
    first = bus.subscribe()
    second = bus.subscribe()
    event = {"event": "test"}

    assert bus.subscriber_count == 2
    bus.publish(event)

    assert first.get_nowait() == event
    assert second.get_nowait() == event
    bus.unsubscribe(first)
    assert bus.subscriber_count == 1
    bus.unsubscribe(second)
    assert bus.subscriber_count == 0


def test_event_bus_drops_oldest_for_slow_subscriber() -> None:
    bus = EventBus(queue_size=1)
    queue = bus.subscribe()
    oldest = {"sequence": 1}
    newest = {"sequence": 2}

    bus.publish(oldest)
    bus.publish(newest)

    assert queue.get_nowait() == newest


def test_event_bus_isolates_subscriber_delivery_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus = EventBus()
    failing = bus.subscribe()
    healthy = bus.subscribe()
    event = {"event": "test"}

    def fail_delivery(item: Any) -> None:
        raise RuntimeError("subscriber failed")

    monkeypatch.setattr(failing, "put_nowait", fail_delivery)

    bus.publish(event)

    assert healthy.get_nowait() == event


async def test_success_lifecycle_events_publish_after_transitions(
    client: TestClient,
) -> None:
    bus = client.app.state.bus
    assert bus is get_event_bus()
    queue = bus.subscribe()
    try:
        response = client.post(
            "/jobs",
            json={"type": WORD_COUNT_JOB_TYPE, "payload": {"text": "events"}},
        )
        job_id = response.json()["id"]
        await process_job(job_id)
        events = [queue.get_nowait() for _ in range(3)]
    finally:
        bus.unsubscribe(queue)

    assert [event["event"] for event in events] == [
        JOB_CREATED_EVENT,
        JOB_STARTED_EVENT,
        JOB_SUCCEEDED_EVENT,
    ]
    assert [event["status"] for event in events] == [
        response.json()["status"],
        RUNNING_JOB_STATUS,
        SUCCEEDED_JOB_STATUS,
    ]
    assert all(event["job_id"] == job_id for event in events)
    assert all(datetime.fromisoformat(event["ts"]).tzinfo is not None for event in events)
    assert bus.subscriber_count == 0


async def test_failed_lifecycle_event_is_published(client: TestClient) -> None:
    bus = client.app.state.bus
    queue = bus.subscribe()
    try:
        response = client.post(
            "/jobs", json={"type": WORD_COUNT_JOB_TYPE, "payload": {}}
        )
        job_id = response.json()["id"]
        await process_job(job_id)
        events = [queue.get_nowait() for _ in range(3)]
    finally:
        bus.unsubscribe(queue)

    assert [event["event"] for event in events] == [
        JOB_CREATED_EVENT,
        JOB_STARTED_EVENT,
        JOB_FAILED_EVENT,
    ]
    assert events[-1]["status"] == FAILED_JOB_STATUS
    assert events[-1]["job_id"] == job_id


def test_websocket_streams_filtered_inline_lifecycle_and_unsubscribes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    bus = client.app.state.bus
    unrelated_job_id = uuid4()
    target_job_id = uuid4()
    generated_ids = iter((unrelated_job_id, target_job_id))
    monkeypatch.setattr("app.db.models.uuid4", lambda: next(generated_ids))
    client.app.dependency_overrides.pop(get_job_service)

    assert bus.subscriber_count == 0
    with client.websocket_connect(f"/ws/jobs?job_id={target_job_id}") as websocket:
        assert websocket.receive_json() == {"event": WS_CONNECTED_EVENT}

        unrelated_response = client.post(
            "/jobs",
            json={"type": WORD_COUNT_JOB_TYPE, "payload": {"text": "ignore me"}},
        )
        assert unrelated_response.json()["id"] == str(unrelated_job_id)
        target_response = client.post(
            "/jobs",
            json={"type": WORD_COUNT_JOB_TYPE, "payload": {"text": "stream me"}},
        )
        assert target_response.json()["id"] == str(target_job_id)

        events = [websocket.receive_json() for _ in range(3)]

    assert [event["event"] for event in events] == [
        JOB_CREATED_EVENT,
        JOB_STARTED_EVENT,
        JOB_SUCCEEDED_EVENT,
    ]
    assert all(event["job_id"] == str(target_job_id) for event in events)
    assert bus.subscriber_count == 0


def test_diff_job_states_detects_new_job() -> None:
    assert diff_job_states({}, {"job-1": DEFAULT_JOB_STATUS}) == [
        {
            "event": JOB_CREATED_EVENT,
            "job_id": "job-1",
            "status": DEFAULT_JOB_STATUS,
        }
    ]


@pytest.mark.parametrize(
    ("job_status", "event_name"),
    [
        (RUNNING_JOB_STATUS, JOB_STARTED_EVENT),
        (SUCCEEDED_JOB_STATUS, JOB_SUCCEEDED_EVENT),
        (FAILED_JOB_STATUS, JOB_FAILED_EVENT),
    ],
)
def test_diff_job_states_detects_status_change(
    job_status: str, event_name: str
) -> None:
    assert diff_job_states(
        {"job-1": DEFAULT_JOB_STATUS}, {"job-1": job_status}
    ) == [{"event": event_name, "job_id": "job-1", "status": job_status}]


def test_diff_job_states_ignores_unchanged_jobs() -> None:
    states = {"job-1": RUNNING_JOB_STATUS}

    assert diff_job_states(states, states.copy()) == []


def test_inline_lifespan_does_not_start_status_poller(client: TestClient) -> None:
    assert not hasattr(client.app.state, "status_poller_task")


async def _next_event(queue: "asyncio.Queue[Event]", timeout: float = 1.0) -> Event:
    return await asyncio.wait_for(queue.get(), timeout)


async def test_prefect_poller_publishes_transitions_without_spurious_or_duplicate_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Speed the poll loop up so the test stays fast but still exercises real ticks.
    monkeypatch.setattr("app.events.JOB_STATUS_POLL_INTERVAL_S", 0.01)
    engine, session_factory = create_database(str(tmp_path / "poller.db"))
    await init_db(engine)
    try:
        # A job that already exists before the poller starts (e.g. from a prior run).
        async with session_factory() as session:
            existing = Job(
                type=WORD_COUNT_JOB_TYPE,
                payload={"text": "old"},
                status=SUCCEEDED_JOB_STATUS,
            )
            session.add(existing)
            await session.commit()

        bus = EventBus()
        queue = bus.subscribe()
        poller = asyncio.create_task(poll_job_states(session_factory, bus))
        try:
            # The pre-existing job underwent no transition, so the first ticks
            # must not publish any lifecycle event for it.
            await asyncio.sleep(0.05)
            assert queue.empty()

            # A newly created job: JobService publishes job.created on POST; the
            # out-of-process worker will drive the remaining transitions.
            async with session_factory() as session:
                job = Job(type=WORD_COUNT_JOB_TYPE, payload={"text": "new"})
                session.add(job)
                await session.commit()
                job_id = job.id
            bus.publish(create_job_event(JOB_CREATED_EVENT, job_id, DEFAULT_JOB_STATUS))

            # The only job.created is the one from POST; the poller must not add a
            # second one when it observes the still-pending row.
            first = await _next_event(queue)
            assert first["event"] == JOB_CREATED_EVENT
            assert first["job_id"] == job_id

            async with session_factory() as session:
                stored = await session.get(Job, job_id)
                assert stored is not None
                stored.status = RUNNING_JOB_STATUS
                await session.commit()
            started = await _next_event(queue)
            assert started["event"] == JOB_STARTED_EVENT
            assert started["job_id"] == job_id

            async with session_factory() as session:
                stored = await session.get(Job, job_id)
                assert stored is not None
                stored.status = SUCCEEDED_JOB_STATUS
                await session.commit()
            succeeded = await _next_event(queue)
            assert succeeded["event"] == JOB_SUCCEEDED_EVENT
            assert succeeded["job_id"] == job_id

            # Drain any trailing events; none may be a duplicate creation.
            await asyncio.sleep(0.05)
            leftovers = []
            while not queue.empty():
                leftovers.append(queue.get_nowait())
            assert all(event["event"] != JOB_CREATED_EVENT for event in leftovers)
        finally:
            poller.cancel()
            with suppress(asyncio.CancelledError):
                await poller
    finally:
        await engine.dispose()


def test_prefect_lifespan_cancels_status_poller(tmp_path: Path) -> None:
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: Settings(
        db_path=str(tmp_path / "prefect.db"), worker_mode=PREFECT_WORKER_MODE
    )

    with TestClient(application):
        poller_task = application.state.status_poller_task
        assert not poller_task.done()

    assert poller_task.cancelled()
