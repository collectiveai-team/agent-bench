"""D2 detector: DELETE on a non-pending (succeeded/failed) job must not crash."""
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient


def test_delete_non_pending_job_returns_204(client: TestClient, db_path: Path) -> None:
    resp = client.post(
        "/jobs", json={"type": "word_count", "payload": {"text": "hello"}}
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # Advance the job to succeeded state directly in the DB.
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE jobs SET status='succeeded', result='{}' WHERE id=?", (job_id,)
        )

    # Deleting a completed job must succeed (204), not crash with 500.
    with TestClient(client.app, raise_server_exceptions=False) as tc:
        delete_resp = tc.delete(f"/jobs/{job_id}")

    assert delete_resp.status_code == 204, (
        f"DELETE on a succeeded job returned {delete_resp.status_code}, expected 204"
    )
