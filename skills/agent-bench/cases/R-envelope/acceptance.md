# Acceptance criteria — R-envelope

Frozen item count: **10**

Each row is one observable criterion. Stage 2 copies `probes/test_probe.py`
to `probes/test_probe.py` in the solver's working copy root, then runs each
`verification_command` verbatim in that root and determines pass/fail from the
output alone.

Items AC-01 through AC-08 are **error-site probes**. Each covers one distinct
error-triggering scenario and checks both the `Content-Type` header and all
five required RFC 7807 members. Items AC-09 and AC-10 verify that success
paths are unchanged.

**Gates (`uv run ruff check .` and bare `uv run pytest -q`) are NOT
included as rows here.** They are scored separately by Stage 2 and must not be
re-run as acceptance criteria to avoid double-counting.

---

## R-family scoring inputs

Stage 2 must populate these fields in `verdict.family_outcome`:

### site_coverage

```
site_coverage = (AC-01 through AC-08 items that pass) / 8
```

File-level coverage is not used because a correct implementation that adds
exception handlers in `app/main.py` may legitimately leave `app/routes/jobs.py`
unmodified; penalising that approach by measuring file diffs would reward
unnecessary churn. See `sites.md` for the full rationale.

Stage 2 writes the ratio as a float in `[0, 1]` to
`verdict.family_outcome.site_coverage`.

### regression_free

```
regression_free = 1  if verdict.gates_passed AND verdict.probes.passed == verdict.probes.total
                  0  otherwise
```

This is all-or-nothing. A single base-suite failure or a single probe failure
sets the term to 0. Stage 2 writes this to
`verdict.family_outcome.regression_free`.

### scope_creep_ratio

```
scope_creep_ratio = files_outside_site_list / total_files_touched
```

Where:
- `total_files_touched` comes from `git diff --name-only` against the
  `_base-taskflow@1` base commit.
- In-scope files (do NOT count toward the numerator):
  `app/main.py`, `app/routes/jobs.py`, `tests/test_jobs_api.py`
- All other touched files count toward the numerator.
- If the solver adds new files (e.g. `app/errors.py`), those count as
  out-of-scope ONLY if they are not imported from an in-scope file; a helper
  module that only `app/main.py` imports is still logically in-scope and is
  excluded from the numerator at the evaluator's discretion.

Stage 2 writes this to `verdict.family_outcome.scope_creep_ratio`.

---

## Acceptance table

| id | criterion | verification_command |
|---|---|---|
| AC-01 | `GET /jobs/{id}` with an unknown id returns 404 with `Content-Type: application/problem+json` and a body containing all five RFC 7807 members (`type`, `title`, `status`, `detail`, `instance`) where `status == 404`. | `uv run pytest probes/test_probe.py -q -k test_get_unknown_job_404_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-02 | `DELETE /jobs/{id}` with an unknown id returns 404 with `Content-Type: application/problem+json` and a well-formed problem+json body where `status == 404`. | `uv run pytest probes/test_probe.py -q -k test_delete_unknown_job_404_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-03 | `DELETE /jobs/{id}` on a running job returns 409 with `Content-Type: application/problem+json` and a well-formed problem+json body where `status == 409`. | `uv run pytest probes/test_probe.py -q -k test_delete_running_job_409_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-04 | `GET /jobs?status=bogus` returns 422 with `Content-Type: application/problem+json` and a well-formed problem+json body where `status == 422` (application-level `InvalidJobListQueryError` path). | `uv run pytest probes/test_probe.py -q -k test_list_invalid_status_422_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-05 | `GET /jobs?limit=0` returns 422 with `Content-Type: application/problem+json` and a well-formed problem+json body where `status == 422` (application-level `InvalidJobListQueryError` path, out-of-range limit). | `uv run pytest probes/test_probe.py -q -k test_list_invalid_limit_422_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. AC-04 and AC-05 are independently falsifiable: a solver that handles only the status-filter branch fails AC-04; one that handles only the limit branch fails AC-05. | — |
| AC-06 | `POST /jobs` with an invalid `type` value returns 422 with `Content-Type: application/problem+json` and a well-formed problem+json body where `status == 422` (framework-level `RequestValidationError` path). | `uv run pytest probes/test_probe.py -q -k test_create_invalid_job_type_422_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. AC-06 and AC-07 are independently falsifiable: AC-06 tests the Literal-enum validation branch; AC-07 tests the dict-type validation branch. A solver that overrides `RequestValidationError` but only for one validation sub-type would fail one and pass the other. | — |
| AC-07 | `POST /jobs` with a non-dict `payload` value returns 422 with `Content-Type: application/problem+json` and a well-formed problem+json body where `status == 422` (framework-level `RequestValidationError` path). | `uv run pytest probes/test_probe.py -q -k test_create_non_dict_payload_422_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-08 | An unhandled exception in a route handler returns 500 with `Content-Type: application/problem+json` and a well-formed problem+json body where `status == 500`. | `uv run pytest probes/test_probe.py -q -k test_unhandled_exception_500_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. The probe injects a deliberate `RuntimeError` via a dynamically-added test route. | — |
| AC-09 | `GET /health` returns 200 with `Content-Type: application/json` (not `application/problem+json`) and body `{"status": "ok"}` unchanged. | `uv run pytest probes/test_probe.py -q -k test_health_success_is_not_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-10 | `POST /jobs` with a valid body returns 201 with `Content-Type: application/json` (not `application/problem+json`) and a body containing all required job fields. | `uv run pytest probes/test_probe.py -q -k test_create_job_success_shape_is_unchanged 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
