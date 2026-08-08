# Probe validation record — L-taskflow

## Full-pass run

**Date:** 2026-08-08

**Source directory:** `/Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol`

**Note on commit identity:** The implementation was never committed in the source repository. Branch `bench-r4` still points at the scaffold commit (`9edeaa6`); the complete implementation exists only as untracked files in the working tree. The SHA below identifies the scaffold commit, not the implementation.

**Scaffold commit SHA:** `9edeaa6`

**Command used:**

```bash
SRC=/Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol
rm -rf /tmp/agb-probe-check
rsync -a --exclude '.git' --exclude '.orquestalite' --exclude '__pycache__' \
      --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude '.venv' \
      "$SRC/" /tmp/agb-probe-check/
cp skills/agent-bench/cases/L-taskflow/probes/test_probe.py /tmp/agb-probe-check/tests/
cd /tmp/agb-probe-check && uv sync && uv run pytest tests/test_probe.py -q; cd -
```

**Output:**

```
..............                                                           [100%]
=============================== warnings summary ===============================
/private/tmp/agb-probe-check/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
14 passed, 1 warning in 10.52s
```

**Result:** 14/14 passed. All probes pass against this known-good implementation.

The deprecation warning (httpx vs httpx2 with starlette.testclient) is a version-skew warning from the test client library, not a probe defect. It does not affect pass/fail.

## Targeted-failure run

**Date:** 2026-08-08

**Break applied:** In `/tmp/agb-probe-check/app/worker/flow.py`, the `execute` task's `WORD_COUNT_JOB_TYPE` branch was changed to return `"chars": 0` instead of `"chars": len(text)`:

```python
# original
return {"words": len(words), "chars": len(text)}
# broken
return {"words": len(words), "chars": 0}  # deliberately broken for probe validation
```

This violates the exact-math criterion for the `word_count` job type without touching any other code path.

**Command used:**

```bash
SRC=/Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol
R=/Users/lionelchamorro/Projects/collectiveai/agent-bench-build
rm -rf /tmp/agb-probe-check
rsync -a --exclude '.git' --exclude '.orquestalite' --exclude '__pycache__' \
      --exclude '.pytest_cache' --exclude '.ruff_cache' \
      "$SRC/" /tmp/agb-probe-check/
cp "$R/skills/agent-bench/cases/L-taskflow/probes/test_probe.py" /tmp/agb-probe-check/tests/
# break applied to /tmp/agb-probe-check/app/worker/flow.py
cd /tmp/agb-probe-check && ./.venv/bin/python -m pytest tests/test_probe.py -q
```

**Output:**

```
.....F........                                                           [100%]
=================================== FAILURES ===================================
_________________________ test_result_word_count_exact _________________________

    def test_result_word_count_exact(fresh):
        client, _ = fresh
        text = "Hello  world hello"  # 3 words, 18 chars (double space preserved)
        job = _create(client, "word_count", {"text": text})
        assert job["status"] == "pending" and job["result"] is None
        done = _wait_terminal(client, job["id"])
        assert done["status"] == "succeeded"
>       assert done["result"] == {"words": 3, "chars": 18}
E       AssertionError: assert {'words': 3, 'chars': 0} == {'words': 3, 'chars': 18}

tests/test_probe.py:151: AssertionError
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_probe.py::test_result_word_count_exact - AssertionError: assert {'words': 3, 'chars': 0} == {'words': 3, 'chars': 18}
1 failed, 13 passed, 1 warning in 10.01s
```

**Result:** Exactly 1 failure (`tests/test_probe.py::test_result_word_count_exact`). All 13 other probe tests continued to pass. The probe correctly discriminates this requirement.

## Cleanup

After both validation runs the temporary directory was removed:

```bash
rm -rf /tmp/agb-probe-check
```
