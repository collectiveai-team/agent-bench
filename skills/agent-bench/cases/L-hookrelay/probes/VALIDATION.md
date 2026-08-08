# Probe validation record — L-hookrelay

## Full-pass run

**Date:** 2026-08-08

**Source directory:** `/Users/lionelchamorro/Projects/personal/hookrelay-r4-gpt-sol`

**Note on commit identity:** The implementation was never committed in the source repository. Branch `bench-r4` still points at the scaffold commit; the complete implementation exists only as untracked files in the working tree. The SHA below identifies the scaffold commit, not the implementation.

**Scaffold commit SHA:** `f3ffad5` (`chore: scaffold hookrelay benchmark round 2 base`) — branch `bench-r4` still points here; the delivered implementation was untracked on top of it and was never committed.

**Command used:**

```bash
SRC=/Users/lionelchamorro/Projects/personal/hookrelay-r4-gpt-sol
R=/Users/lionelchamorro/Projects/collectiveai/agent-bench-build
rm -rf /tmp/agb-hr-check
rsync -a --exclude '.git' --exclude '.orquestalite' --exclude '__pycache__' \
      --exclude '.pytest_cache' --exclude '.ruff_cache' \
      "$SRC/" /tmp/agb-hr-check/
cp "$R/skills/agent-bench/cases/L-hookrelay/probes/test_probe.py" /tmp/agb-hr-check/tests/
cd /tmp/agb-hr-check && ./.venv/bin/python -m pytest tests/test_probe.py -q
```

**Output:**

```
...............                                                          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /private/tmp/agb-hr-check/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
15 passed, 1 warning in 3.46s
```

**Result:** 15/15 passed. All probes pass against this known-good implementation.

The deprecation warning (httpx vs httpx2 with starlette.testclient) is a version-skew warning from the test client library, not a probe defect. It does not affect pass/fail.

## Targeted-failure run

**Date:** 2026-08-08

**Break applied:** In `/tmp/agb-hr-check/app/services/dispatcher.py`, the `_signature` function was changed to use the wrong HMAC key:

```python
# original
return hmac.new(secret.encode(), signed_content, hashlib.sha256).hexdigest()
# broken
return hmac.new(b"wrong-key", signed_content, hashlib.sha256).hexdigest()  # deliberately broken for probe validation
```

This violates the HMAC-SHA256 signing contract — the receiver will compute a different digest from the actual subscription secret — without touching any other code path. The delivery still completes with status `delivered` (the receiver in the probe responds 200 regardless of headers), but the signature comparison in the probe fails.

**Command used:**

```bash
SRC=/Users/lionelchamorro/Projects/personal/hookrelay-r4-gpt-sol
R=/Users/lionelchamorro/Projects/collectiveai/agent-bench-build
rm -rf /tmp/agb-hr-check
rsync -a --exclude '.git' --exclude '.orquestalite' --exclude '__pycache__' \
      --exclude '.pytest_cache' --exclude '.ruff_cache' \
      "$SRC/" /tmp/agb-hr-check/
cp "$R/skills/agent-bench/cases/L-hookrelay/probes/test_probe.py" /tmp/agb-hr-check/tests/
# break applied to /tmp/agb-hr-check/app/services/dispatcher.py
cd /tmp/agb-hr-check && ./.venv/bin/python -m pytest tests/test_probe.py -q
```

**Output:**

```
......F........                                                          [100%]
=================================== FAILURES ===================================
____________________ test_delivery_happy_path_and_signature ____________________

tmp_path = PosixPath('/private/var/folders/fr/1hzjgk3n61z65276whgbl5v40000gn/T/pytest-of-lionelchamorro/pytest-1877/test_delivery_happy_path_and_s0')

    def test_delivery_happy_path_and_signature(tmp_path):
        receiver = Receiver()
        with _make_client(tmp_path, receiver) as client:
            _mk_sub(client)
            ev = _mk_event(client)
            assert _wait(
                lambda: _deliveries(client, status="delivered")["total"] == 1
            ), "delivery never completed"
            assert len(receiver.requests) == 1, "expected exactly one POST to the receiver"
            req = receiver.requests[0]
            ts = req["headers"].get("x-hookrelay-timestamp")
            sig = req["headers"].get("x-hookrelay-signature")
            assert ts and sig, "signature headers missing"
            assert _tz_aware(ts), "signature timestamp is not timezone-aware"
            expected = hmac.new(
                SECRET.encode(), f"{ts}.".encode() + req["body"], hashlib.sha256
            ).hexdigest()
>           assert sig == expected, "HMAC does not verify against the sent bytes"
E           AssertionError: HMAC does not verify against the sent bytes
E           assert '53f1ab3b2bbd...fae3a6b83b3bd' == 'f28b07d1a3ff...45455be4a5c66'
E             
E             - f28b07d1a3ff5e2ce2710a9625da4dba5cea230a0d2b83d84ac45455be4a5c66
E             + 53f1ab3b2bbd8b55acb4b7d40986eb05d35641a7965039338abfae3a6b83b3bd

tests/test_probe.py:344: AssertionError
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /private/tmp/agb-hr-check/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_probe.py::test_delivery_happy_path_and_signature - AssertionError: HMAC does not verify against the sent bytes
1 failed, 14 passed, 1 warning in 3.41s
```

**Result:** Exactly 1 failure (`tests/test_probe.py::test_delivery_happy_path_and_signature`). All 14 other probe tests continued to pass. The probe correctly discriminates the HMAC signing requirement.

## Cleanup

After both validation runs the temporary directory was removed:

```bash
rm -rf /tmp/agb-hr-check
```

Source repository unchanged: `git -C "$SRC" status --porcelain | wc -l` → `25` (unchanged from baseline).
