"""D4 detector: GET /stats by_type must count by job type, not by job status."""
from fastapi.testclient import TestClient


def test_stats_by_type_uses_type_column(client: TestClient) -> None:
    # Create two word_count jobs and one reverse job.
    r1 = client.post("/jobs", json={"type": "word_count", "payload": {"text": "hello"}})
    assert r1.status_code == 201
    r2 = client.post("/jobs", json={"type": "word_count", "payload": {"text": "world"}})
    assert r2.status_code == 201
    r3 = client.post("/jobs", json={"type": "reverse", "payload": {"text": "hello"}})
    assert r3.status_code == 201

    stats = client.get("/stats")
    assert stats.status_code == 200
    by_type = stats.json()["by_type"]

    # On the clean base, Job.type is used so word_count == 2, reverse == 1.
    # On the patched base, Job.status is used; no job has status == "word_count"
    # or "reverse", so all counts are 0 — the assertions fail.
    assert by_type["word_count"] == 2, (
        f"GET /stats by_type['word_count'] = {by_type['word_count']}; "
        f"expected 2 — the aggregation may be comparing the wrong column"
    )
    assert by_type["reverse"] == 1, (
        f"GET /stats by_type['reverse'] = {by_type['reverse']}; "
        f"expected 1"
    )
    assert by_type["summary_stats"] == 0
