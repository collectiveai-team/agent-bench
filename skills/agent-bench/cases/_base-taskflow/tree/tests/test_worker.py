import sqlite3
from datetime import datetime
from pathlib import Path
from time import monotonic

import pytest
from fastapi.testclient import TestClient

from app.core.config import (
    DEFAULT_JOB_STATUS,
    FAILED_JOB_STATUS,
    JOB_TYPES,
    PROCESS_JOB_DEPLOYMENT_NAME,
    REVERSE_JOB_TYPE,
    SUCCEEDED_JOB_STATUS,
    SUMMARY_STATS_JOB_TYPE,
    WORD_COUNT_JOB_TYPE,
)
from app.routes.jobs import get_job_service
from app.worker.flow import process_job


@pytest.mark.parametrize(
    ("job_type", "text", "expected_result"),
    [
        (
            WORD_COUNT_JOB_TYPE,
            "hello prefect",
            {"words": 2, "chars": 13},
        ),
        (
            REVERSE_JOB_TYPE,
            "Taskflow",
            {"text": "wolfksaT"},
        ),
        (
            SUMMARY_STATS_JOB_TYPE,
            "Alpha beta\nalpha Gamma",
            {"lines": 2, "words": 4, "unique_words": 3},
        ),
    ],
)
async def test_process_job_succeeds_for_each_type(
    client: TestClient,
    job_type: str,
    text: str,
    expected_result: dict[str, int | str],
) -> None:
    create_response = client.post(
        "/jobs", json={"type": job_type, "payload": {"text": text}}
    )
    assert create_response.status_code == 201
    created_job = create_response.json()
    assert created_job["status"] == DEFAULT_JOB_STATUS

    await process_job(created_job["id"])

    processed_job = client.get(f"/jobs/{created_job['id']}").json()
    assert processed_job["status"] == SUCCEEDED_JOB_STATUS
    assert processed_job["result"] == expected_result
    assert processed_job["error"] is None
    started_at = datetime.fromisoformat(processed_job["started_at"])
    finished_at = datetime.fromisoformat(processed_job["finished_at"])
    assert started_at.tzinfo is not None
    assert finished_at.tzinfo is not None
    assert started_at <= finished_at


@pytest.mark.parametrize("payload", [{}, {"text": ""}])
async def test_process_job_persists_payload_failure(
    client: TestClient, payload: dict[str, str]
) -> None:
    create_response = client.post(
        "/jobs", json={"type": WORD_COUNT_JOB_TYPE, "payload": payload}
    )
    job_id = create_response.json()["id"]

    await process_job(job_id)

    failed_job = client.get(f"/jobs/{job_id}").json()
    assert failed_job["status"] == FAILED_JOB_STATUS
    assert failed_job["result"] is None
    assert failed_job["error"]
    assert failed_job["started_at"] is not None
    assert failed_job["finished_at"] is not None


async def test_process_job_persists_unknown_type_failure(
    client: TestClient, db_path: Path
) -> None:
    create_response = client.post(
        "/jobs",
        json={"type": WORD_COUNT_JOB_TYPE, "payload": {"text": "content"}},
    )
    job_id = create_response.json()["id"]
    unknown_type = "unknown"
    assert unknown_type not in JOB_TYPES
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE jobs SET type = ? WHERE id = ?", (unknown_type, job_id)
        )

    await process_job(job_id)

    with sqlite3.connect(db_path) as connection:
        failed_job = connection.execute(
            "SELECT status, error, started_at, finished_at FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
    assert failed_job is not None
    job_status, error, started_at, finished_at = failed_job
    assert job_status == FAILED_JOB_STATUS
    assert error
    assert started_at is not None
    assert finished_at is not None


def test_inline_post_reaches_terminal_status(client: TestClient) -> None:
    client.app.dependency_overrides.pop(get_job_service)
    create_response = client.post(
        "/jobs",
        json={"type": WORD_COUNT_JOB_TYPE, "payload": {"text": "inline worker"}},
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]

    deadline = monotonic() + 10
    while monotonic() < deadline:
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] in (SUCCEEDED_JOB_STATUS, FAILED_JOB_STATUS):
            break
    else:
        pytest.fail("inline job did not reach a terminal status before the deadline")

    assert job["status"] == SUCCEEDED_JOB_STATUS
    assert job["result"] == {"words": 2, "chars": 13}


def test_process_job_deployment_name() -> None:
    deployment = process_job.to_deployment(name=PROCESS_JOB_DEPLOYMENT_NAME)

    assert deployment.name == PROCESS_JOB_DEPLOYMENT_NAME
