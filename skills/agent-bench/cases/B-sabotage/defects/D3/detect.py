"""D3 detector: PATCH /jobs/{id} must not overwrite fields absent from the request body."""
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient


def test_partial_update_preserves_error_field(client: TestClient, db_path: Path) -> None:
    resp = client.post(
        "/jobs", json={"type": "word_count", "payload": {"text": "hello"}}
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # Inject an error value directly in the DB so the job has a non-null error.
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE jobs SET status='failed', error='something went wrong' WHERE id=?",
            (job_id,),
        )

    get_resp = client.get(f"/jobs/{job_id}")
    assert get_resp.json()["error"] == "something went wrong"

    # PATCH with only payload — error field is absent from the request.
    patch_resp = client.patch(f"/jobs/{job_id}", json={"payload": {"text": "updated"}})

    if patch_resp.status_code == 405:
        # No PATCH endpoint on the clean base — defect is not present.
        return

    assert patch_resp.status_code == 200

    # The error field must survive the partial update.
    after = client.get(f"/jobs/{job_id}").json()
    assert after["error"] == "something went wrong", (
        f"Partial PATCH clobbered the error field: was 'something went wrong', "
        f"now {after['error']!r}"
    )
