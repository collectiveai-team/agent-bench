"""
R-envelope probe suite.

These probes are hidden from the solver. They verify that every error response in the
taskflow service has been migrated to the RFC 7807 problem-details envelope
(application/problem+json with type, title, status, detail, and instance),
that success responses are byte-identical to their pre-migration shape,
and that HTTP-originated events on the event bus carry a request_id.

All probes are black-box: they exercise the public HTTP surface only.
No internal modules are imported.
"""

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROBLEM_MEDIA_TYPE = "application/problem+json"
REQUIRED_MEMBERS = {"type", "title", "status", "detail", "instance"}


def _assert_problem_json(response, expected_status: int) -> dict:
    """Assert the response is a well-formed RFC 7807 problem+json envelope."""
    ct = response.headers.get("content-type", "")
    assert PROBLEM_MEDIA_TYPE in ct, (
        f"Expected Content-Type to contain {PROBLEM_MEDIA_TYPE!r}, got {ct!r}"
    )
    body = response.json()
    missing = REQUIRED_MEMBERS - body.keys()
    assert not missing, f"Problem+json body missing members: {missing}"
    assert isinstance(body["type"], str) and body["type"], "type must be a non-empty string"
    assert isinstance(body["title"], str) and body["title"], "title must be a non-empty string"
    assert body["status"] == expected_status, (
        f"status member {body['status']!r} must match HTTP status {expected_status}"
    )
    assert isinstance(body["detail"], str) and body["detail"], (
        "detail must be a non-empty string"
    )
    assert isinstance(body["instance"], str) and body["instance"], (
        "instance must be a non-empty string"
    )
    assert body["instance"].startswith("/"), (
        f"instance must start with '/', got {body['instance']!r}"
    )
    return body


# ---------------------------------------------------------------------------
# Site 1: GET /jobs/{job_id} — 404 when job not found
# ---------------------------------------------------------------------------


def test_get_unknown_job_404_is_problem_json(client: TestClient) -> None:
    response = client.get(f"/jobs/{uuid4()}")

    assert response.status_code == 404
    _assert_problem_json(response, 404)


# ---------------------------------------------------------------------------
# Site 2: DELETE /jobs/{job_id} — 404 when job not found
# ---------------------------------------------------------------------------


def test_delete_unknown_job_404_is_problem_json(client: TestClient) -> None:
    response = client.delete(f"/jobs/{uuid4()}")

    assert response.status_code == 404
    _assert_problem_json(response, 404)


# ---------------------------------------------------------------------------
# Site 3: DELETE /jobs/{job_id} — 409 when job is running
# ---------------------------------------------------------------------------


def test_delete_running_job_409_is_problem_json(client: TestClient, db_path: Path) -> None:
    create_resp = client.post(
        "/jobs", json={"type": "word_count", "payload": {"text": "probe test"}}
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE jobs SET status = 'running' WHERE id = ?", (job_id,))

    response = client.delete(f"/jobs/{job_id}")

    assert response.status_code == 409
    _assert_problem_json(response, 409)


# ---------------------------------------------------------------------------
# Site 4: GET /jobs — 422 when query parameters are invalid (app-level)
# Application raises InvalidJobListQueryError → HTTPException(422).
# ---------------------------------------------------------------------------


def test_list_invalid_status_422_is_problem_json(client: TestClient) -> None:
    response = client.get("/jobs", params={"status": "not_a_real_status"})

    assert response.status_code == 422
    _assert_problem_json(response, 422)


def test_list_invalid_limit_422_is_problem_json(client: TestClient) -> None:
    response = client.get("/jobs", params={"limit": 0})  # below MIN_JOB_LIMIT

    assert response.status_code == 422
    _assert_problem_json(response, 422)


# ---------------------------------------------------------------------------
# Site 5: POST /jobs — 422 from FastAPI RequestValidationError
# FastAPI raises RequestValidationError when Pydantic rejects the body before
# the handler is reached; this is distinct from the application-level path.
# ---------------------------------------------------------------------------


def test_create_invalid_job_type_422_is_problem_json(client: TestClient) -> None:
    response = client.post(
        "/jobs", json={"type": "unsupported_type", "payload": {"text": "hello"}}
    )

    assert response.status_code == 422
    _assert_problem_json(response, 422)


def test_create_non_dict_payload_422_is_problem_json(client: TestClient) -> None:
    response = client.post(
        "/jobs", json={"type": "word_count", "payload": "not_a_dict"}
    )

    assert response.status_code == 422
    _assert_problem_json(response, 422)


# ---------------------------------------------------------------------------
# Site 6: 500 — unhandled exception in a route handler
# Added dynamically so no application code is modified.
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_bomb(app):
    """Client with an extra route that raises an unhandled exception."""
    router = APIRouter()

    @router.get("/_probe_bomb")
    async def _bomb():
        raise RuntimeError("deliberate probe error")

    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_unhandled_exception_500_is_problem_json(client_with_bomb: TestClient) -> None:
    response = client_with_bomb.get("/_probe_bomb")

    assert response.status_code == 500
    _assert_problem_json(response, 500)


# ---------------------------------------------------------------------------
# Success-path invariant: success responses must NOT be wrapped in problem+json
# ---------------------------------------------------------------------------


def test_health_success_is_not_problem_json(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    ct = response.headers.get("content-type", "")
    assert PROBLEM_MEDIA_TYPE not in ct, (
        "Success response must not use application/problem+json"
    )
    assert response.json() == {"status": "ok"}


def test_create_job_success_shape_is_unchanged(client: TestClient) -> None:
    response = client.post(
        "/jobs", json={"type": "word_count", "payload": {"text": "hello world"}}
    )

    assert response.status_code == 201
    ct = response.headers.get("content-type", "")
    assert PROBLEM_MEDIA_TYPE not in ct, (
        "Success response must not use application/problem+json"
    )
    body = response.json()
    required = {"id", "type", "status", "payload", "result", "error", "created_at"}
    assert required.issubset(body.keys()), f"Success body missing fields: {required - body.keys()}"


# ---------------------------------------------------------------------------
# Propagation probe: job.created event must carry request_id
#
# Every event published to the bus from an HTTP request must include a
# request_id field. The field is injected by create_job_event when it
# receives a RequestContext (propagated explicitly through the service and
# repository layers, never via contextvars or module-level globals).
# ---------------------------------------------------------------------------


def test_job_created_event_includes_request_id(client: TestClient) -> None:
    """job.created event must carry a non-empty request_id string."""
    bus = client.app.state.bus
    queue = bus.subscribe()
    try:
        resp = client.post(
            "/jobs", json={"type": "word_count", "payload": {"text": "probe"}}
        )
        assert resp.status_code == 201
        # job.created is published synchronously inside service.create before
        # control returns to the route handler, so get_nowait() is safe here.
        event = queue.get_nowait()
    finally:
        bus.unsubscribe(queue)

    assert "request_id" in event, (
        "job.created event must include 'request_id'; "
        f"keys present: {list(event.keys())}"
    )
    assert isinstance(event["request_id"], str) and event["request_id"], (
        "request_id must be a non-empty string"
    )
