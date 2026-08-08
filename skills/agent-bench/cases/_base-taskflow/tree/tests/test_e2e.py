from fastapi.testclient import TestClient

from app.core.config import (
    DEFAULT_JOB_STATUS,
    FAILED_JOB_STATUS,
    JOB_CREATED_EVENT,
    JOB_STARTED_EVENT,
    JOB_SUCCEEDED_EVENT,
    REVERSE_JOB_TYPE,
    RUNNING_JOB_STATUS,
    SUCCEEDED_JOB_STATUS,
    SUMMARY_STATS_JOB_TYPE,
    WORD_COUNT_JOB_TYPE,
    WS_CONNECTED_EVENT,
)

JOB_CASES = [
    (
        WORD_COUNT_JOB_TYPE,
        "hello world",
        {"words": 2, "chars": 11},
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
]


def test_public_inline_lifecycle(inline_client: TestClient) -> None:
    created_ids: set[str] = set()

    with inline_client.websocket_connect("/ws/jobs") as websocket:
        assert websocket.receive_json() == {"event": WS_CONNECTED_EVENT}

        for job_type, text, expected_result in JOB_CASES:
            create_response = inline_client.post(
                "/jobs", json={"type": job_type, "payload": {"text": text}}
            )
            assert create_response.status_code == 201
            job_id = create_response.json()["id"]
            created_ids.add(job_id)

            events = [websocket.receive_json() for _ in range(3)]
            assert [event["event"] for event in events] == [
                JOB_CREATED_EVENT,
                JOB_STARTED_EVENT,
                JOB_SUCCEEDED_EVENT,
            ]
            assert all(event["job_id"] == job_id for event in events)

            get_response = inline_client.get(f"/jobs/{job_id}")
            assert get_response.status_code == 200
            job = get_response.json()
            assert job["status"] == SUCCEEDED_JOB_STATUS
            assert job["result"] == expected_result

    list_response = inline_client.get(
        "/jobs", params={"status": SUCCEEDED_JOB_STATUS}
    )
    assert list_response.status_code == 200
    listed_jobs = list_response.json()
    assert listed_jobs["total"] == len(JOB_CASES)
    assert {job["id"] for job in listed_jobs["jobs"]} == created_ids

    stats_response = inline_client.get("/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["jobs"] == {
        DEFAULT_JOB_STATUS: 0,
        RUNNING_JOB_STATUS: 0,
        SUCCEEDED_JOB_STATUS: len(JOB_CASES),
        FAILED_JOB_STATUS: 0,
        "total": len(JOB_CASES),
    }
    assert stats["by_type"] == {
        WORD_COUNT_JOB_TYPE: 1,
        REVERSE_JOB_TYPE: 1,
        SUMMARY_STATS_JOB_TYPE: 1,
    }
    assert stats["avg_duration_s"] is not None
