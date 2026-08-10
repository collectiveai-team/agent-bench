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
44 passed, 1 warning in 10.52s
```

---

## Migration applied

The migration added both halves:

**Envelope half (Half 1):**
- `app/main.py` — added handlers for `HTTPException`, `RequestValidationError`,
  and `Exception`; extracted a `_problem_response` helper
- `tests/test_jobs_api.py` — updated the two error-body assertions (lines 55
  and 71) that asserted `{"detail": "..."}` to assert the problem+json shape

**Propagation half (Half 2):**
- `app/context.py` — new file defining `RequestContext` frozen dataclass and
  `get_request_context` FastAPI dependency
- `app/events.py` — `create_job_event` gains `ctx: RequestContext | None = None`
  parameter; includes `request_id` in event when ctx is not None
- `app/services/jobs.py` — all 5 service methods gain `ctx: RequestContext` as
  first positional parameter
- `app/repositories/jobs.py` — HTTP-path methods (`create`, `list`, `count`,
  `stats`, `delete`) gain `ctx: RequestContext` as first positional parameter;
  `get` gains `ctx: RequestContext | None` (required but nullable since it is
  also called from the Prefect worker); `mark_running` and `record_result`
  already had optional ctx
- `app/routes/jobs.py` — all route handlers gain `ctx: RequestContextDependency`
  and pass it to the service
- `app/routes/stats.py` — `get_stats` gains `ctx: RequestContextDependency` and
  passes it to the service
- `app/worker/flow.py` — `_get_job` updated to call
  `repository.get(None, job_id)`, explicitly signalling no HTTP context
- `tests/test_stats.py` — `seed_jobs` helper updated to create a sentinel
  `RequestContext` for direct repository calls in tests

---

## Transcript 1 — full-pass run (all 11 probes pass)

Command:
```bash
cd /tmp/agb-envelope-ref
cp /Users/lionelchamorro/Projects/collectiveai/agent-bench-build/skills/agent-bench/cases/R-envelope/probes/test_probe.py tests/
./.venv/bin/python -m pytest tests/test_probe.py -v
```

Output (warnings and deprecation notice omitted):

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
asyncio: mode=Mode.AUTO

collected 11 items

tests/test_probe.py::test_get_unknown_job_404_is_problem_json PASSED     [  9%]
tests/test_probe.py::test_delete_unknown_job_404_is_problem_json PASSED  [ 18%]
tests/test_probe.py::test_delete_running_job_409_is_problem_json PASSED  [ 27%]
tests/test_probe.py::test_list_invalid_status_422_is_problem_json PASSED [ 36%]
tests/test_probe.py::test_list_invalid_limit_422_is_problem_json PASSED  [ 45%]
tests/test_probe.py::test_create_invalid_job_type_422_is_problem_json PASSED [ 54%]
tests/test_probe.py::test_create_non_dict_payload_422_is_problem_json PASSED [ 63%]
tests/test_probe.py::test_unhandled_exception_500_is_problem_json PASSED [ 72%]
tests/test_probe.py::test_health_success_is_not_problem_json PASSED      [ 81%]
tests/test_probe.py::test_create_job_success_shape_is_unchanged PASSED   [ 90%]
tests/test_probe.py::test_job_created_event_includes_request_id PASSED   [100%]

======================== 11 passed, 1 warning in 3.28s =========================
```

Combined run (base suite + probes):

```
55 passed, 1 warning in 10.52s
```

Interpretation: all six envelope error sites covered, propagation probe
confirmed request_id in job.created event, both success-path invariants
confirmed, base suite regression-free.

---

## Transcript 2 — targeted-failure run (1 probe fails)

Reverted propagation site: `create_job_event` in `app/events.py` was modified
to accept `ctx: RequestContext | None = None` but not include `request_id` in
the event dict (the `if ctx is not None:` block was removed, while the
parameter declaration was kept). All envelope handlers and all other
propagation call sites remained unchanged.

Command: same as above.

Output (warnings omitted):

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
asyncio: mode=Mode.AUTO

collected 11 items

tests/test_probe.py::test_get_unknown_job_404_is_problem_json PASSED     [  9%]
tests/test_probe.py::test_delete_unknown_job_404_is_problem_json PASSED  [ 18%]
tests/test_probe.py::test_delete_running_job_409_is_problem_json PASSED  [ 27%]
tests/test_probe.py::test_list_invalid_status_422_is_problem_json PASSED [ 36%]
tests/test_probe.py::test_list_invalid_limit_422_is_problem_json PASSED  [ 45%]
tests/test_probe.py::test_create_invalid_job_type_422_is_problem_json PASSED [ 54%]
tests/test_probe.py::test_create_non_dict_payload_422_is_problem_json PASSED [ 63%]
tests/test_probe.py::test_unhandled_exception_500_is_problem_json PASSED [ 72%]
tests/test_probe.py::test_health_success_is_not_problem_json PASSED      [ 81%]
tests/test_probe.py::test_create_job_success_shape_is_unchanged PASSED   [ 90%]
tests/test_probe.py::test_job_created_event_includes_request_id FAILED   [100%]

FAILED tests/test_probe.py::test_job_created_event_includes_request_id
- AssertionError: job.created event must include 'request_id';
  keys present: ['event', 'job_id', 'status', 'ts']

==================== 1 failed, 10 passed, 1 warning in 3.19s ==================
```

Interpretation: exactly one probe failed (`test_job_created_event_includes_request_id`,
which corresponds to the `create_job_event` propagation site in `app/events.py`).
The ten remaining probes continued to pass, confirming the failure is isolated
to the reverted site.

---

## Confirmation

- The reference implementation was deleted after both runs:
  `rm -rf /tmp/agb-envelope-ref`
- The source repository was not modified:
  `git -C /Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol status --porcelain | wc -l`
  output: `20` (unchanged)

---

## Probe defect log

No defects discovered as of v2 (2026-08-10).

**v1 → v2 changes:**
- Probe count raised from 10 to 11 (added `test_job_created_event_includes_request_id`)
- `_assert_problem_json` tightened: added `assert body["instance"].startswith("/")`
- Revert-one-site test changed from envelope (exception handler removal) to
  propagation (create_job_event stops using ctx)
