"""D4 detector: GET /jobs?type=<t> must filter by job type, not by status."""
from fastapi.testclient import TestClient


def test_type_filter_returns_matching_jobs(client: TestClient) -> None:
    # Create one word_count job.
    resp = client.post(
        "/jobs", json={"type": "word_count", "payload": {"text": "hello"}}
    )
    assert resp.status_code == 201

    list_resp = client.get("/jobs", params={"type": "word_count"})
    assert list_resp.status_code == 200
    body = list_resp.json()

    # At least the job we created must appear.
    # On the clean base the ?type param is unknown and ignored, so all jobs are
    # returned — the assertion passes.
    # On the patched base the filter incorrectly uses Job.status == "word_count",
    # which never matches (status is one of pending/running/succeeded/failed), so
    # the list is empty — the assertion fails.
    assert len(body["jobs"]) > 0, (
        "GET /jobs?type=word_count returned no jobs even though word_count jobs exist; "
        "the type filter is probably comparing against the wrong column"
    )
