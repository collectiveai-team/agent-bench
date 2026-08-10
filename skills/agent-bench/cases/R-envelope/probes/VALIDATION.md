# R-envelope probe validation record

Validation performed 2026-08-10 against a throwaway reference implementation
at `/tmp/agb-envelope-ref` (base tree copied from
`skills/agent-bench/cases/_base-taskflow/tree` plus `.venv` copied from
the read-only source repository). The reference was deleted after both runs.

---

## Setup

```bash
R=/Users/lionelchamorro/Projects/collectiveai/agent-bench-build
SRC=/Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol
rm -rf /tmp/agb-envelope-ref
cp -R "$R/skills/agent-bench/cases/_base-taskflow/tree" /tmp/agb-envelope-ref
cp -R "$SRC/.venv" /tmp/agb-envelope-ref/.venv
```

Base suite before migration (44 passed — confirms the copy was clean):

```
44 passed, 1 warning in 6.95s
```

---

## Migration applied

The migration added three `exception_handler` registrations to `app/main.py`
and updated two error-body assertions in `tests/test_jobs_api.py`. No
application logic or success-path test was changed. Files touched:

- `app/main.py` — added handlers for `HTTPException`, `RequestValidationError`,
  and `Exception`; extracted a `_problem_response` helper
- `tests/test_jobs_api.py` — updated lines 55 and 71 (which asserted
  `{"detail": "..."}`) to assert the problem+json shape instead

---

## Transcript 1 — full-pass run (all 10 probes pass)

Command:
```bash
cd /tmp/agb-envelope-ref
cp /path/to/probes/test_probe.py tests/
./.venv/bin/python -m pytest tests/test_probe.py -v
```

Output (warnings and Starlette deprecation notice omitted):

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
asyncio: mode=Mode.AUTO

collected 10 items

tests/test_probe.py::test_get_unknown_job_404_is_problem_json PASSED     [ 10%]
tests/test_probe.py::test_delete_unknown_job_404_is_problem_json PASSED  [ 20%]
tests/test_probe.py::test_delete_running_job_409_is_problem_json PASSED  [ 30%]
tests/test_probe.py::test_list_invalid_status_422_is_problem_json PASSED [ 40%]
tests/test_probe.py::test_list_invalid_limit_422_is_problem_json PASSED  [ 50%]
tests/test_probe.py::test_create_invalid_job_type_422_is_problem_json PASSED [ 60%]
tests/test_probe.py::test_create_non_dict_payload_422_is_problem_json PASSED [ 70%]
tests/test_probe.py::test_unhandled_exception_500_is_problem_json PASSED [ 80%]
tests/test_probe.py::test_health_success_is_not_problem_json PASSED      [ 90%]
tests/test_probe.py::test_create_job_success_shape_is_unchanged PASSED   [100%]

======================== 10 passed, 1 warning in 3.47s =========================
```

Combined run (base suite + probes):

```
54 passed, 1 warning in 10.78s
```

Interpretation: all six error sites covered, both success-path invariants
confirmed, base suite regression-free.

---

## Transcript 2 — targeted-failure run (1 probe fails)

Reverted site: the `exception_handler(Exception)` registration was removed
from `app/main.py` (the 500 handler for unhandled exceptions). All other
handlers (for `HTTPException` and `RequestValidationError`) remained in place.

Command: same as above.

Output (warnings omitted):

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
asyncio: mode=Mode.AUTO

collected 10 items

tests/test_probe.py::test_get_unknown_job_404_is_problem_json PASSED     [ 10%]
tests/test_probe.py::test_delete_unknown_job_404_is_problem_json PASSED  [ 20%]
tests/test_probe.py::test_delete_running_job_409_is_problem_json PASSED  [ 30%]
tests/test_probe.py::test_list_invalid_status_422_is_problem_json PASSED [ 40%]
tests/test_probe.py::test_list_invalid_limit_422_is_problem_json PASSED  [ 50%]
tests/test_probe.py::test_create_invalid_job_type_422_is_problem_json PASSED [ 60%]
tests/test_probe.py::test_create_non_dict_payload_422_is_problem_json PASSED [ 70%]
tests/test_probe.py::test_unhandled_exception_500_is_problem_json FAILED [ 80%]
tests/test_probe.py::test_health_success_is_not_problem_json PASSED      [ 90%]
tests/test_probe.py::test_create_job_success_shape_is_unchanged PASSED   [100%]

FAILED tests/test_probe.py::test_unhandled_exception_500_is_problem_json
- AssertionError: Expected Content-Type to contain 'application/problem+json',
  got 'application/json'

==================== 1 failed, 9 passed, 1 warning in 3.24s ===================
```

Interpretation: exactly one probe failed (`test_unhandled_exception_500_is_problem_json`,
which corresponds to site 6 — the `Exception` handler). The nine remaining
probes continued to pass, confirming the failure is isolated to the reverted
site.

---

## Confirmation

- The reference implementation was deleted after both runs:
  `rm -rf /tmp/agb-envelope-ref`
- The source repository was not modified:
  `git -C /Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol status --porcelain | wc -l`
  output: `20` (unchanged)

---

## Probe defect log

No defects discovered as of v1 (2026-08-10).
