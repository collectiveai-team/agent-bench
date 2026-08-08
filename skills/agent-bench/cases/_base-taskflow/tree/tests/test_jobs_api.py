import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import (
    DEFAULT_JOB_OFFSET,
    DEFAULT_JOB_STATUS,
    JOB_STATUSES,
    JOB_TYPES,
    MAX_JOB_LIMIT,
    MIN_JOB_LIMIT,
    RUNNING_JOB_STATUS,
)

JOB_TYPE = JOB_TYPES[0]
JOB_PAYLOAD = {"text": "hello world"}


def test_create_get_delete_job(client: TestClient) -> None:
    create_response = client.post(
        "/jobs", json={"type": JOB_TYPE, "payload": JOB_PAYLOAD}
    )

    assert create_response.status_code == 201
    created_job = create_response.json()
    assert created_job["type"] == JOB_TYPE
    assert created_job["status"] == DEFAULT_JOB_STATUS
    assert created_job["payload"] == JOB_PAYLOAD
    assert created_job["result"] is None
    assert created_job["error"] is None
    assert created_job["created_at"] is not None
    assert created_job["started_at"] is None
    assert created_job["finished_at"] is None

    get_response = client.get(f"/jobs/{created_job['id']}")

    assert get_response.status_code == 200
    assert get_response.json() == created_job

    delete_response = client.delete(f"/jobs/{created_job['id']}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert client.get(f"/jobs/{created_job['id']}").status_code == 404


@pytest.mark.parametrize("method", ["get", "delete"])
def test_unknown_job_returns_404(client: TestClient, method: str) -> None:
    response = getattr(client, method)(f"/jobs/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_running_job_cannot_be_deleted(client: TestClient, db_path: Path) -> None:
    create_response = client.post(
        "/jobs", json={"type": JOB_TYPE, "payload": JOB_PAYLOAD}
    )
    job_id = create_response.json()["id"]
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE jobs SET status = ? WHERE id = ?", (RUNNING_JOB_STATUS, job_id)
        )

    response = client.delete(f"/jobs/{job_id}")

    assert response.status_code == 409
    assert response.json() == {"detail": "job is running"}


def test_unknown_job_type_returns_422(client: TestClient) -> None:
    response = client.post(
        "/jobs", json={"type": "unsupported", "payload": JOB_PAYLOAD}
    )

    assert response.status_code == 422


def test_non_dict_payload_returns_422(client: TestClient) -> None:
    response = client.post("/jobs", json={"type": JOB_TYPE, "payload": []})

    assert response.status_code == 422


def test_list_filters_by_status_and_counts_matching_jobs(
    client: TestClient, db_path: Path
) -> None:
    job_ids = [
        client.post(
            "/jobs", json={"type": JOB_TYPE, "payload": {"index": index}}
        ).json()["id"]
        for index in range(3)
    ]
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE jobs SET status = ? WHERE id = ?",
            (RUNNING_JOB_STATUS, job_ids[1]),
        )

    response = client.get("/jobs", params={"status": RUNNING_JOB_STATUS})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [job["id"] for job in body["jobs"]] == [job_ids[1]]


def test_list_paginates_without_changing_total(client: TestClient) -> None:
    for index in range(3):
        response = client.post(
            "/jobs", json={"type": JOB_TYPE, "payload": {"index": index}}
        )
        assert response.status_code == 201
    all_jobs = client.get("/jobs").json()["jobs"]

    response = client.get("/jobs", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    assert response.json() == {"jobs": all_jobs[1:2], "total": 3}


def test_list_orders_by_created_at_then_id(
    client: TestClient, db_path: Path
) -> None:
    job_ids = [
        client.post(
            "/jobs", json={"type": JOB_TYPE, "payload": {"index": index}}
        ).json()["id"]
        for index in range(3)
    ]
    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            "UPDATE jobs SET created_at = ? WHERE id = ?",
            [
                ("2026-01-02 00:00:00", job_ids[0]),
                ("2026-01-02 00:00:00", job_ids[1]),
                ("2026-01-01 00:00:00", job_ids[2]),
            ],
        )

    response = client.get("/jobs")

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["jobs"]] == [
        *sorted(job_ids[:2]),
        job_ids[2],
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"limit": MIN_JOB_LIMIT - 1},
        {"limit": MAX_JOB_LIMIT + 1},
        {"offset": DEFAULT_JOB_OFFSET - 1},
        {"status": "invalid"},
    ],
)
def test_list_rejects_invalid_query_values(
    client: TestClient, params: dict[str, int | str]
) -> None:
    response = client.get("/jobs", params=params)

    assert response.status_code == 422


def test_list_accepts_every_known_status(client: TestClient) -> None:
    for job_status in JOB_STATUSES:
        response = client.get("/jobs", params={"status": job_status})
        assert response.status_code == 200
