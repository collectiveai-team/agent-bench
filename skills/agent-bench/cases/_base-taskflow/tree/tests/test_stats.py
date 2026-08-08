from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import (
    DEFAULT_JOB_STATUS,
    FAILED_JOB_STATUS,
    REVERSE_JOB_TYPE,
    RUNNING_JOB_STATUS,
    SUCCEEDED_JOB_STATUS,
    SUMMARY_STATS_JOB_TYPE,
    WORD_COUNT_JOB_TYPE,
)
from app.db.session import create_database
from app.repositories.jobs import JobRepository


async def seed_jobs(
    db_path: Path, definitions: list[tuple[str, str, int]]
) -> None:
    started_at = datetime(2026, 1, 1, tzinfo=UTC)
    engine, session_factory = create_database(str(db_path))
    try:
        async with session_factory() as session:
            repository = JobRepository(session)
            for job_type, job_status, duration_s in definitions:
                job = await repository.create(job_type, {"text": "stats"})
                job.status = job_status
                job.started_at = started_at
                job.finished_at = started_at + timedelta(seconds=duration_s)
            await session.commit()
    finally:
        await engine.dispose()


async def test_stats_average_is_null_without_terminal_jobs(
    client: TestClient, db_path: Path
) -> None:
    await seed_jobs(
        db_path,
        [
            (WORD_COUNT_JOB_TYPE, DEFAULT_JOB_STATUS, 100),
            (REVERSE_JOB_TYPE, RUNNING_JOB_STATUS, 200),
        ],
    )

    response = client.get("/stats")

    assert response.status_code == 200
    assert response.json() == {
        "jobs": {
            DEFAULT_JOB_STATUS: 1,
            RUNNING_JOB_STATUS: 1,
            SUCCEEDED_JOB_STATUS: 0,
            FAILED_JOB_STATUS: 0,
            "total": 2,
        },
        "by_type": {WORD_COUNT_JOB_TYPE: 1, REVERSE_JOB_TYPE: 1, SUMMARY_STATS_JOB_TYPE: 0},
        "avg_duration_s": None,
    }


async def test_stats_returns_sql_aggregates(
    client: TestClient, db_path: Path
) -> None:
    await seed_jobs(
        db_path,
        [
            (WORD_COUNT_JOB_TYPE, DEFAULT_JOB_STATUS, 100),
            (REVERSE_JOB_TYPE, RUNNING_JOB_STATUS, 200),
            (WORD_COUNT_JOB_TYPE, SUCCEEDED_JOB_STATUS, 10),
            (SUMMARY_STATS_JOB_TYPE, FAILED_JOB_STATUS, 20),
        ],
    )

    response = client.get("/stats")

    assert response.status_code == 200
    assert response.json() == {
        "jobs": {
            DEFAULT_JOB_STATUS: 1,
            RUNNING_JOB_STATUS: 1,
            SUCCEEDED_JOB_STATUS: 1,
            FAILED_JOB_STATUS: 1,
            "total": 4,
        },
        "by_type": {WORD_COUNT_JOB_TYPE: 2, REVERSE_JOB_TYPE: 1, SUMMARY_STATS_JOB_TYPE: 1},
        "avg_duration_s": 15.0,
    }
