# R-envelope — sealed site lists

This file is **evaluation material and is never placed in the solver's working
copy.** A solver who reads it has access to the complete map of what the
evaluator will check and can game the coverage metric. Do not reference this
file in any prompt or spec fragment visible to the solver.

---

## Half 1 — Envelope sites

### Generator command

```bash
cd skills/agent-bench/cases/_base-taskflow/tree
grep -rn 'raise HTTPException' app/ | sort
```

Run this command at the root of the agent-bench repository against the base
tree (commit pinned at `_base-taskflow@1`) to reproduce the initial site list.

### Why this command was chosen (and what was rejected)

The brief suggested:
```bash
grep -rn 'HTTPException\|JSONResponse\|status_code=4\|status_code=5' app/ | sort
```

That command was evaluated and rejected for two reasons:

1. **False positives.** It catches import lines (e.g.
   `from fastapi import ... HTTPException`) that are not error sites.
   `JSONResponse` is not used anywhere in the base application, so that
   branch produces no output but adds noise to the intent.

2. **Redundancy.** The `status_code=4` and `status_code=5` patterns only
   catch literals. Every literal that matters is already on a line that
   also contains `raise HTTPException`, so the added patterns yield no
   additional sites.

The refined command `grep -rn 'raise HTTPException' app/ | sort` finds only
the lines where an HTTP error response is actively raised by application code,
which is the correct definition of a site for this refactor.

### What the generator does NOT catch

The generator operates only on application code in `app/`. It intentionally
omits two additional error-response paths that the solver must also cover:

- **Framework-level 422 (RequestValidationError).** FastAPI raises
  `RequestValidationError` internally when a request body or query parameter
  fails Pydantic validation (e.g. `POST /jobs` with an invalid `type` value).
  This error path exists at framework level, not in `app/` source code. The
  solver must register a custom `exception_handler(RequestValidationError)` to
  intercept it; the generator cannot find this registration in the base tree
  because it does not exist yet.

- **Unhandled exception → 500.** FastAPI returns a plain `{"detail":
  "Internal Server Error"}` for any exception not handled by the application.
  This path also lives at framework level. The solver must register a custom
  `exception_handler(Exception)` to cover it.

These two framework-level paths are represented as sites 5 and 6 below. They
are documented rather than generated because no grep on the base tree can find
a registration that does not yet exist.

### Site list (frozen at `_base-taskflow@1`)

Generator output (run 2026-08-10):

```
app/routes/jobs.py:46:        raise HTTPException(status_code=422, detail=str(error)) from error
app/routes/jobs.py:55:        raise HTTPException(status_code=404, detail=str(error)) from error
app/routes/jobs.py:63:        raise HTTPException(status_code=404, detail=str(error)) from error
app/routes/jobs.py:65:        raise HTTPException(status_code=409, detail=str(error)) from error
```

| # | file:line | HTTP status | Trigger |
|---|---|---|---|
| 1 | `app/routes/jobs.py:46` | 422 | `GET /jobs` — `InvalidJobListQueryError` (invalid status, limit, or offset) |
| 2 | `app/routes/jobs.py:55` | 404 | `GET /jobs/{job_id}` — `JobNotFoundError` |
| 3 | `app/routes/jobs.py:63` | 404 | `DELETE /jobs/{job_id}` — `JobNotFoundError` |
| 4 | `app/routes/jobs.py:65` | 409 | `DELETE /jobs/{job_id}` — `JobRunningError` |
| 5 | `app/main.py` (to be added) | 422 | `POST /jobs` — FastAPI `RequestValidationError` for invalid body |
| 6 | `app/main.py` (to be added) | 500 | Any route handler — unhandled `Exception` |

**Total envelope sites: 6** (4 in application code + 2 framework-level)

### site_coverage for the envelope half

Because a correct implementation can cover all six envelope sites by adding
exception handlers to `app/main.py` without modifying `app/routes/jobs.py`,
file-level coverage would penalise correct implementations that use the global
handler approach. Coverage of the envelope half is therefore **probe-based**:

```
envelope_coverage = (error-site probes that pass) / 8
```

The eight error-site probes are AC-01 through AC-08 in `acceptance.md`. Each
probe exercises one distinct error-triggering scenario. Envelope coverage feeds
into `regression_free` (not `site_coverage`) — see acceptance.md.

---

## Half 2 — Propagation sites

### Generator command

```bash
cd skills/agent-bench/cases/_base-taskflow/tree
grep -rn 'async def ' app/services/jobs.py app/repositories/jobs.py | sort
```

### Site list (frozen at `_base-taskflow@1`)

Generator output (run 2026-08-10):

```
app/repositories/jobs.py:113:    async def delete(self, job: Job) -> None:
app/repositories/jobs.py:20:    async def create(self, job_type: str, payload: dict[str, object]) -> Job:
app/repositories/jobs.py:26:    async def get(self, job_id: str) -> Job | None:
app/repositories/jobs.py:29:    async def mark_running(self, job: Job) -> Job:
app/repositories/jobs.py:35:    async def record_result(
app/repositories/jobs.py:54:    async def list(
app/repositories/jobs.py:64:    async def count(self, job_status: str | None) -> int:
app/repositories/jobs.py:71:    async def stats(self) -> dict[str, Any]:
app/services/jobs.py:53:    async def create(self, job_create: JobCreate) -> Job:
app/services/jobs.py:62:    async def get(self, job_id: str) -> Job:
app/services/jobs.py:68:    async def list(
app/services/jobs.py:87:    async def stats(self) -> dict[str, object]:
app/services/jobs.py:90:    async def delete(self, job_id: str) -> None:
```

**Total propagation signatures: 13** across 2 files.

Additional sealed propagation site (not in grep output):

| # | file | description |
|---|---|---|
| 14 | `app/events.py` | `create_job_event` function — must accept `ctx: RequestContext | None = None` and include `request_id` in event when ctx is provided |

**Total propagation files: 3** — `app/services/jobs.py`, `app/repositories/jobs.py`,
`app/events.py`

### site_coverage for the propagation half

Propagation coverage is **file-based** per `scoring.md`'s definition:

```
propagation_coverage = (propagation sealed files touched) / 3
```

Where the 3 sealed files are `app/services/jobs.py`, `app/repositories/jobs.py`,
and `app/events.py`. Stage 2 determines "touched" from `git diff --name-only`
against the `_base-taskflow@1` base commit.

---

## Combined site_coverage

```
site_coverage = propagation_coverage
             = (propagation sealed files touched) / 3
```

The envelope half does not contribute to `site_coverage` directly because
file-level coverage would penalise the correct global-handler approach. The
envelope half is measured entirely through `regression_free` (probes AC-01
through AC-08 must all pass). The propagation half is measured through both
`site_coverage` (files touched) and `regression_free` (probe AC-11 must pass).

Stage 2 writes the ratio as a float in `[0, 1]` to
`verdict.family_outcome.site_coverage`.

---

## In-scope files for scope_creep_ratio

The following files are the legitimate change targets for this task. Touching
files outside this list counts as scope creep.

| File | Why in scope |
|---|---|
| `app/main.py` | Exception handlers must be registered here. |
| `app/routes/jobs.py` | Envelope sites 1–4; also the HTTP entry point for ctx injection. |
| `app/routes/stats.py` | HTTP entry point for ctx injection on the stats endpoint. |
| `app/context.py` | New file defining `RequestContext` and `get_request_context`. In scope if imported from `app/routes/jobs.py` or `app/routes/stats.py`. |
| `app/events.py` | `create_job_event` gains ctx parameter (propagation sealed site). |
| `app/services/jobs.py` | All service methods gain ctx parameter (propagation sealed file). |
| `app/repositories/jobs.py` | All repository methods gain ctx parameter (propagation sealed file). |
| `tests/test_jobs_api.py` | Contains assertions against the old `{"detail": "..."}` shape that must be updated. |

**Scope_creep_ratio computation:**

```
scope_creep_ratio = files_touched_outside_the_eight_above / total_files_touched
```

Where `files_touched` is derived from `git diff --name-only` against the
base commit (`_base-taskflow@1`).

**Deterministic rule for new files:** A new file (not in the base tree) is
in scope if and only if it is imported transitively from a file already in the
in-scope list AND contains only error-handling or context-propagation logic.
Any new file that is not imported from an in-scope file, or that contains
business logic beyond error handling or context propagation, counts toward the
scope-creep numerator.

---

## Staleness policy

This file must be regenerated whenever the base version increments. Regenerate
by running both generator commands above, re-auditing for the framework-level
paths and the additional `create_job_event` site, and updating both site
tables, the frozen totals, and the date line.
