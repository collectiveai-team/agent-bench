# Acceptance criteria — R-envelope

Frozen item count: **11**

Each row is one observable criterion. Stage 2 copies `probes/test_probe.py`
to `probes/test_probe.py` in the solver's working copy root, then runs each
`verification_command` verbatim in that root and determines pass/fail from the
output alone.

Items AC-01 through AC-08 are **envelope probes**. Each covers one distinct
error-triggering scenario and checks both the `Content-Type` header and all
five required RFC 7807 members. Items AC-09 and AC-10 verify that success
paths are unchanged. Item AC-11 is the **propagation probe**: it verifies that
the `job.created` event on the event bus carries `request_id`.

**Gates (`uv run ruff check .` and bare `uv run pytest -q`) are NOT
included as rows here.** They are scored separately by Stage 2 and must not be
re-run as acceptance criteria to avoid double-counting.

---

## R-family scoring inputs

Stage 2 must populate these fields in `verdict.family_outcome`:

### site_coverage

`site_coverage` is **file-based** (per `scoring.md`):

```
site_coverage = (propagation sealed files touched by the solver) / 3
```

The three propagation sealed files are:

- `app/services/jobs.py`
- `app/repositories/jobs.py`
- `app/events.py`

Stage 2 determines "touched" from `git diff --name-only` against the
`_base-taskflow@1` base commit. The ratio is `[0, 1]` with granularity of
1/3.

**Why the envelope half does not feed site_coverage:** A correct envelope
implementation adds exception handlers in `app/main.py` and does not need to
modify `app/routes/jobs.py`. Measuring envelope coverage by file diff would
penalise that approach. The envelope half is measured through `regression_free`
(AC-01 through AC-08 must all pass). See `sites.md` for the full rationale.

Stage 2 writes the ratio to `verdict.family_outcome.site_coverage`.

### regression_free

```
regression_free = 1  if verdict.gates_passed AND verdict.probes.passed == verdict.probes.total
                  0  otherwise
```

This is all-or-nothing. A single base-suite failure or a single probe failure
(AC-01 through AC-11) sets the term to 0. Stage 2 writes this to
`verdict.family_outcome.regression_free`.

### scope_creep_ratio

```
scope_creep_ratio = files_outside_in_scope_list / total_files_touched
```

Where:

- `total_files_touched` comes from `git diff --name-only` against the
  `_base-taskflow@1` base commit.
- In-scope files (do NOT count toward the numerator):
  `app/main.py`, `app/routes/jobs.py`, `app/routes/stats.py`,
  `app/context.py` (if applicable), `app/events.py`, `app/services/jobs.py`,
  `app/repositories/jobs.py`, `tests/test_jobs_api.py`
- **Deterministic rule for new files:** A new file is in scope if and only if
  it is imported transitively from a file already on the in-scope list AND
  contains only error-handling or context-propagation logic. Any new file not
  imported from an in-scope file, or that contains business logic beyond error
  handling or context propagation, counts toward the numerator.
- All other touched files count toward the numerator.

Stage 2 writes this to `verdict.family_outcome.scope_creep_ratio`.

---

## Acceptance table

| id | criterion | verification_command |
|---|---|---|
| AC-01 | `GET /jobs/{id}` with an unknown id returns 404 with `Content-Type: application/problem+json` and a body containing all five RFC 7807 members (`type`, `title`, `status`, `detail`, `instance`) where `status == 404` and `instance` starts with `/`. | `uv run pytest probes/test_probe.py -q -k test_get_unknown_job_404_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-02 | `DELETE /jobs/{id}` with an unknown id returns 404 with `Content-Type: application/problem+json` and a well-formed problem+json body where `status == 404` and `instance` starts with `/`. | `uv run pytest probes/test_probe.py -q -k test_delete_unknown_job_404_is_problem_json 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-03 | `DELETE /jobs/{id}` on a running job returns 409 with `Content-Type: application/problem+json` and a well-formed problem+json body where `status == 409` and `instance` starts with `/`. | `uv run pytest probes/test_probe.py -q -k test_delete_running_job_409_is_problem_json 2>&1 \| tail -2` |
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
| AC-11 | `POST /jobs` with a valid body publishes a `job.created` event on the event bus that includes a non-empty `request_id` string field. The `request_id` is created once per HTTP request and propagated explicitly (not via contextvars or module-level globals) through the service and repository layers. | `uv run pytest probes/test_probe.py -q -k test_job_created_event_includes_request_id 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. This is the propagation probe. Reverted-site test: modify `create_job_event` to accept `ctx` but not include `request_id` in the event — AC-11 fails and AC-01 through AC-10 all pass. | — |
