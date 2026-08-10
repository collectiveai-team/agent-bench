"""D3 detector: job payload must be preserved after the job completes."""
from fastapi.testclient import TestClient


def test_payload_preserved_after_job_completes(inline_client: TestClient) -> None:
    original_payload = {"text": "hello world"}

    with inline_client.websocket_connect("/ws/jobs") as ws:
        ws.receive_json()  # {"event": "connected"}

        resp = inline_client.post(
            "/jobs", json={"type": "word_count", "payload": original_payload}
        )
        assert resp.status_code == 201
        job_id = resp.json()["id"]

        # Drain the three lifecycle events so the job has reached a terminal state.
        for _ in range(3):  # job.created, job.started, job.succeeded
            ws.receive_json()

    get_resp = inline_client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200
    job = get_resp.json()
    assert job["status"] == "succeeded"

    assert job["payload"] == original_payload, (
        f"job payload was overwritten after completion; "
        f"expected {original_payload!r}, got {job['payload']!r}"
    )
