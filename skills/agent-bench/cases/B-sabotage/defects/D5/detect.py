"""D5 detector: GET /jobs with offset past the total must return an empty list."""
from fastapi.testclient import TestClient


def test_offset_beyond_total_returns_empty(client: TestClient) -> None:
    # Seed two jobs so total > 0.
    for i in range(2):
        r = client.post("/jobs", json={"type": "word_count", "payload": {"text": f"job {i}"}})
        assert r.status_code == 201

    # Request with offset far beyond the total.
    resp = client.get("/jobs", params={"limit": 10, "offset": 100})
    assert resp.status_code == 200
    body = resp.json()

    # Correct behaviour: offset past the end returns an empty list.
    # The defect clamps offset to max(0, total - limit), returning the last page instead.
    assert len(body["jobs"]) == 0, (
        f"Expected empty list for offset 100 with total={body['total']}, "
        f"got {len(body['jobs'])} job(s); pagination is off-by-one at the boundary"
    )
