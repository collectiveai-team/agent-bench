# Probe validation record — S-ledger

## Full-pass run

**Date:** 2026-08-08

**Reference directory:** `/tmp/agb-ledger-ref` (throwaway; not committed)

**Venv source:** copied from `/Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol/.venv` (fastapi 0.139.1, sqlalchemy 2.0.51, aiosqlite 0.22.1, httpx 0.28.1, pytest 9.1.1, pytest-asyncio 1.4.0, pydantic-settings 2.14.2). The reference implementation was written from scratch against `spec/features.md` and was never committed.

**Command used:**

```bash
cp skills/agent-bench/cases/S-ledger/probes/test_probe.py /tmp/agb-ledger-ref/tests/test_probe.py
cd /tmp/agb-ledger-ref && ./.venv/bin/python -m pytest tests/test_probe.py -q
```

**Output:**

```
..........                                                               [100%]
=============================== warnings summary ===============================
tests/test_probe.py:25
  /private/tmp/agb-ledger-ref/tests/test_probe.py:25: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
10 passed, 1 warning in 3.58s
```

**Result:** 10/10 passed. All probes pass against this known-good implementation.

The deprecation warning (httpx vs httpx2 with starlette.testclient) is a version-skew warning from the test client library, not a probe defect. It does not affect pass/fail.

## Targeted-failure run

**Date:** 2026-08-08

**Break applied:** Two changes to the throwaway implementation in `/tmp/agb-ledger-ref`:

1. In `app/services/transfers.py`, the idempotency-key lookup block was commented out:
   ```python
   # Idempotency check — deliberately removed for probe validation
   # existing = await self._transfer_repo.get_by_key(idempotency_key)
   # if existing is not None:
   #     if existing.request_body_hash != body_hash:
   #         raise HTTPException(status_code=409, detail="idempotency_key_conflict")
   #     return existing, False
   ```

2. In `app/db/models.py`, the `unique=True` constraint was removed from `transfers.idempotency_key`:
   ```python
   idempotency_key: Mapped[str] = mapped_column(String, nullable=False)  # unique=True removed
   ```

These two changes together simulate a naive implementation that has no idempotency key logic at all. Without the DB uniqueness constraint, the replay attempts do not raise a DB integrity error; they simply create duplicate transfers, exposing both idempotency probe failures cleanly.

**Command used:**

```bash
cd /tmp/agb-ledger-ref && ./.venv/bin/python -m pytest tests/test_probe.py -q
```

**Output:**

```
..FF......                                                               [100%]
=================================== FAILURES ===================================
_______ test_idempotent_replay_same_body_returns_same_id_and_moves_once ________

client = <starlette.testclient.TestClient object at 0x10d3f1430>

    def test_idempotent_replay_same_body_returns_same_id_and_moves_once(client):
        ...
        status2, body2 = _transfer(client, src["id"], dst["id"], 100, key=key)
>       assert status2 == 200, f"expected 200 on replay, got {status2}: {body2}"
E       AssertionError: expected 200 on replay, got 201: {'id': '81e8ea7f-...', 'amount_minor': 100, ...}
E       assert 201 == 200

tests/test_probe.py:134: AssertionError
_______________ test_idempotent_replay_different_body_conflicts ________________

client = <starlette.testclient.TestClient object at 0x10d473530>

    def test_idempotent_replay_different_body_conflicts(client):
        ...
        r = client.post(
            "/transfers",
            json={"from_account_id": src["id"], "to_account_id": dst["id"], "amount_minor": 200},
            headers={"Idempotency-Key": key},
        )
>       assert r.status_code == 409
E       assert 201 == 409
E        +  where 201 = <Response [201 Created]>.status_code

tests/test_probe.py:154: AssertionError
=============================== warnings summary ===============================
tests/test_probe.py:25
  /private/tmp/agb-ledger-ref/tests/test_probe.py:25: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_probe.py::test_idempotent_replay_same_body_returns_same_id_and_moves_once
FAILED tests/test_probe.py::test_idempotent_replay_different_body_conflicts
2 failed, 8 passed, 1 warning in 0.33s
```

**Result:** Exactly 2 failures (`test_idempotent_replay_same_body_returns_same_id_and_moves_once` and `test_idempotent_replay_different_body_conflicts`). All 8 other probe tests continued to pass. The probes correctly discriminate the idempotency key requirement.

## Cleanup

After both validation runs the throwaway reference was deleted:

```bash
rm -rf /tmp/agb-ledger-ref
```

The source venv was never modified; the reference existed only in `/tmp/agb-ledger-ref` and is now gone.
