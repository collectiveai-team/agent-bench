"""D1 detector: created_at must carry UTC timezone info across the DB round-trip."""
from fastapi.testclient import TestClient


def test_created_at_preserves_timezone_on_round_trip(client: TestClient) -> None:
    resp = client.post("/jobs", json={"type": "word_count", "payload": {"text": "hello"}})
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    get_resp = client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200
    created_at_str = get_resp.json()["created_at"]

    # UTC-aware datetimes are serialised with a "Z" suffix or "+00:00" offset.
    # A naive datetime (the defect) has neither.
    assert "Z" in created_at_str or "+" in created_at_str, (
        f"created_at lost timezone info after DB round-trip: {created_at_str!r}"
    )
