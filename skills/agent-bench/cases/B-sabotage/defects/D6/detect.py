"""D6 detector: job.created event must not be published before the DB transaction commits."""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient


def test_event_not_published_before_commit(app, monkeypatch) -> None:
    async def fail_commit(self) -> None:
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(AsyncSession, "commit", fail_commit)

    with TestClient(app, raise_server_exceptions=False) as tc:
        bus = tc.app.state.bus
        q = bus.subscribe()
        tc.post("/jobs", json={"type": "word_count", "payload": {"text": "hello"}})
        has_event = not q.empty()
        bus.unsubscribe(q)

    # On the clean base: commit() fails before publish() is reached → queue empty → PASS.
    # On the patched base: publish() runs before commit() → queue has event → FAIL.
    assert not has_event, (
        "job.created event was published before the DB transaction committed; "
        "a rollback would have emitted a phantom event"
    )
