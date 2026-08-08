# Probe validation record — S-ledger

## Full-pass run

**Date:** 2026-08-08

**Reference directory:** `/tmp/agb-ledger-ref` (throwaway; not committed)

**Venv source:** copied from `/Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol/.venv` (fastapi 0.139.1, sqlalchemy 2.0.51, aiosqlite 0.22.1, httpx 0.28.1, pytest 9.1.1, pytest-asyncio 1.4.0, pydantic-settings 2.14.2). The reference implementation was written from scratch against `spec/features.md` and was never committed.

**Command used:**

```bash
cp skills/agent-bench/cases/S-ledger/probes/test_probe.py /tmp/agb-ledger-ref/tests/test_probe.py
cd /tmp/agb-ledger-ref && ./.venv/bin/python -m pytest tests/test_probe.py -v
```

**Output:**

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0 -- /private/tmp/agb-ledger-ref/.venv/bin/python
cachedir: .pytest_cache
rootdir: /private/tmp/agb-ledger-ref
plugins: asyncio-1.4.0, anyio-4.14.2
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 12 items

tests/test_probe.py::test_credit_then_balance PASSED                     [  8%]
tests/test_probe.py::test_transfer_moves_exact_minor_units PASSED        [ 16%]
tests/test_probe.py::test_transfer_records_transaction_rows PASSED       [ 25%]
tests/test_probe.py::test_idempotent_replay_same_body_returns_same_id_and_moves_once PASSED [ 33%]
tests/test_probe.py::test_idempotent_replay_different_body_conflicts PASSED [ 41%]
tests/test_probe.py::test_missing_idempotency_key_rejected PASSED        [ 50%]
tests/test_probe.py::test_non_positive_amount_rejected PASSED            [ 58%]
tests/test_probe.py::test_insufficient_funds PASSED                      [ 66%]
tests/test_probe.py::test_unknown_account PASSED                         [ 75%]
tests/test_probe.py::test_pagination_default_limit_and_ordering PASSED   [ 83%]
tests/test_probe.py::test_pagination_offset_past_end PASSED              [ 91%]
tests/test_probe.py::test_timestamps_are_timezone_aware_after_roundtrip PASSED [100%]

=============================== warnings summary ===============================
tests/test_probe.py:29
  /private/tmp/agb-ledger-ref/tests/test_probe.py:29: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

tests/test_probe.py::test_idempotent_replay_different_body_conflicts
  /private/tmp/agb-ledger-ref/.venv/lib/python3.12/site-packages/aiosqlite/core.py:127: DeprecationWarning: There is no current event loop
    future = asyncio.get_event_loop().create_future()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 12 passed, 2 warnings in 0.47s ========================
```

**Result:** 12/12 passed. All probes pass against this known-good implementation.

The deprecation warnings (httpx vs httpx2 with starlette.testclient; aiosqlite event loop) are version-skew warnings from library internals, not probe defects. They do not affect pass/fail.

## Targeted-failure run

**Date:** 2026-08-08

**Break applied:** Two changes to the throwaway implementation in `/tmp/agb-ledger-ref`:

1. In `app/services/transfers.py`, the idempotency-key lookup block was removed:
   ```python
   # idempotency check removed — simulates naive implementation
   ```

2. In `app/db/models.py`, the `unique=True` constraint was removed from `transfers.idempotency_key`:
   ```python
   idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
   ```

These two changes together simulate a naive implementation that has no idempotency key logic at all. Without the DB uniqueness constraint, replay attempts do not raise a DB integrity error; they simply create duplicate transfers, exposing both idempotency probe failures cleanly.

**Command used:**

```bash
cd /tmp/agb-ledger-ref && ./.venv/bin/python -m pytest tests/test_probe.py -v
```

**Output:**

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0 -- /private/tmp/agb-ledger-ref/.venv/bin/python
cachedir: .pytest_cache
rootdir: /private/tmp/agb-ledger-ref
plugins: asyncio-1.4.0, anyio-4.14.2
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 12 items

tests/test_probe.py::test_credit_then_balance PASSED                     [  8%]
tests/test_probe.py::test_transfer_moves_exact_minor_units PASSED        [ 16%]
tests/test_probe.py::test_transfer_records_transaction_rows PASSED       [ 25%]
tests/test_probe.py::test_idempotent_replay_same_body_returns_same_id_and_moves_once FAILED [ 33%]
tests/test_probe.py::test_idempotent_replay_different_body_conflicts FAILED [ 41%]
tests/test_probe.py::test_missing_idempotency_key_rejected PASSED        [ 50%]
tests/test_probe.py::test_non_positive_amount_rejected PASSED            [ 58%]
tests/test_probe.py::test_insufficient_funds PASSED                      [ 66%]
tests/test_probe.py::test_unknown_account PASSED                         [ 75%]
tests/test_probe.py::test_pagination_default_limit_and_ordering PASSED   [ 83%]
tests/test_probe.py::test_pagination_offset_past_end PASSED              [ 91%]
tests/test_probe.py::test_timestamps_are_timezone_aware_after_roundtrip PASSED [100%]

=================================== FAILURES ===================================
_______ test_idempotent_replay_same_body_returns_same_id_and_moves_once ________

client = <starlette.testclient.TestClient object at 0x10ccf85f0>

    def test_idempotent_replay_same_body_returns_same_id_and_moves_once(client):
        """Two identical POST /transfers with the same Idempotency-Key: second returns 200 with the same id; balances do not change a second time."""
        src = _make_account(client, "src")
        dst = _make_account(client, "dst")
        _credit(client, src["id"], 1000)
        key = str(uuid.uuid4())
        status1, body1 = _transfer(client, src["id"], dst["id"], 100, key=key)
        assert status1 == 201
        src_after_first = _balance(client, src["id"])
        dst_after_first = _balance(client, dst["id"])
        # replay with the same key and same body
        status2, body2 = _transfer(client, src["id"], dst["id"], 100, key=key)
>       assert status2 == 200, f"expected 200 on replay, got {status2}: {body2}"
E       AssertionError: expected 200 on replay, got 201: {'id': 'edd14d5f-a2ab-4e18-bd52-dd7ae4abae0f', 'from_account_id': '8fee5fc3-f5d7-40a8-a311-1cfd00808f48', 'to_account_id': 'f5e23a9c-6654-44bf-b2fc-311cccef3f4a', 'amount_minor': 100, 'created_at': '2026-08-08T19:29:01.670199Z'}
E       assert 201 == 200

tests/test_probe.py:162: AssertionError
_______________ test_idempotent_replay_different_body_conflicts ________________

client = <starlette.testclient.TestClient object at 0x10cc267e0>

    def test_idempotent_replay_different_body_conflicts(client):
        """Same Idempotency-Key with a changed amount_minor returns 409."""
        src = _make_account(client, "src")
        dst = _make_account(client, "dst")
        _credit(client, src["id"], 2000)
        key = str(uuid.uuid4())
        status1, _ = _transfer(client, src["id"], dst["id"], 100, key=key)
        assert status1 == 201
        # same key, different amount — must conflict
        r = client.post(
            "/transfers",
            json={"from_account_id": src["id"], "to_account_id": dst["id"], "amount_minor": 200},
            headers={"Idempotency-Key": key},
        )
>       assert r.status_code == 409
E       assert 201 == 409
E        +  where 201 = <Response [201 Created]>.status_code

tests/test_probe.py:182: AssertionError
=============================== warnings summary ===============================
tests/test_probe.py:29
  /private/tmp/agb-ledger-ref/tests/test_probe.py:29: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_probe.py::test_idempotent_replay_same_body_returns_same_id_and_moves_once
FAILED tests/test_probe.py::test_idempotent_replay_different_body_conflicts
=================== 2 failed, 10 passed, 1 warning in 0.42s ====================
```

**Result:** Exactly 2 failures (`test_idempotent_replay_same_body_returns_same_id_and_moves_once` and `test_idempotent_replay_different_body_conflicts`). All 10 other probe tests continued to pass. The probes correctly discriminate the idempotency key requirement.

## Cleanup

After both validation runs the throwaway reference was deleted:

```bash
rm -rf /tmp/agb-ledger-ref
```

The source venv was never modified; the reference existed only in `/tmp/agb-ledger-ref` and is now gone.
