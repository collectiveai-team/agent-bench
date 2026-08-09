"""D7 detector: DELETE /jobs/<unknown-id> must return 404, not crash with 500.

This defect removes the existence check from the service and weakens the test
so the suite stays green while the acceptance criterion is silently violated.
"""
from uuid import uuid4

from fastapi.testclient import TestClient


def test_delete_unknown_job_returns_404(app) -> None:
    """Deleting a non-existent job must return 404, not an unhandled server error."""
    with TestClient(app, raise_server_exceptions=False) as tc:
        response = tc.delete(f"/jobs/{uuid4()}")

    assert response.status_code == 404, (
        f"DELETE /jobs/<unknown> returned {response.status_code}, expected 404; "
        "the existence check may have been removed from the delete handler"
    )
