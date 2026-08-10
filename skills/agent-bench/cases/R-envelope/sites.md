# R-envelope — sealed error site list

This file is **evaluation material and is never placed in the solver's working
copy.** A solver who reads it has access to the complete map of what the
evaluator will check and can game the coverage metric. Do not reference this
file in any prompt or spec fragment visible to the solver.

---

## Generator command

```bash
cd skills/agent-bench/cases/_base-taskflow/tree
grep -rn 'raise HTTPException' app/ | sort
```

Run this command at the root of the agent-bench repository against the base
tree (commit pinned at `_base-taskflow@1`) to reproduce the initial site list.
A future evaluator can re-run it against a solver's tree to audit whether the
solver changed or preserved these lines.

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

---

## Site list (frozen at `_base-taskflow@1`)

Generator output (run 2026-08-10):

```
app/routes/jobs.py:46:        raise HTTPException(status_code=422, detail=str(error)) from error
app/routes/jobs.py:55:        raise HTTPException(status_code=404, detail=str(error)) from error
app/routes/jobs.py:63:        raise HTTPException(status_code=404, detail=str(error)) from error
app/routes/jobs.py:65:        raise HTTPException(status_code=409, detail=str(error)) from error
```

### Complete site table

| # | file:line | HTTP status | Trigger |
|---|---|---|---|
| 1 | `app/routes/jobs.py:46` | 422 | `GET /jobs` — `InvalidJobListQueryError` (invalid status, limit, or offset) |
| 2 | `app/routes/jobs.py:55` | 404 | `GET /jobs/{job_id}` — `JobNotFoundError` |
| 3 | `app/routes/jobs.py:63` | 404 | `DELETE /jobs/{job_id}` — `JobNotFoundError` |
| 4 | `app/routes/jobs.py:65` | 409 | `DELETE /jobs/{job_id}` — `JobRunningError` |
| 5 | `app/main.py` (to be added) | 422 | `POST /jobs` — FastAPI `RequestValidationError` for invalid body |
| 6 | `app/main.py` (to be added) | 500 | Any route handler — unhandled `Exception` |

**Total sealed sites: 6**

---

## In-scope files for scope_creep_ratio

The following three files are the legitimate change targets for this
refactor. A solver may need to touch all or some of them, depending on
implementation approach. Touching files outside this list counts as scope
creep.

| File | Why in scope |
|---|---|
| `app/main.py` | Exception handlers must be registered here (or in a module imported here). |
| `app/routes/jobs.py` | Contains sites 1–4; a solver may change individual raises rather than using global handlers. |
| `tests/test_jobs_api.py` | Contains two assertions against the old `{"detail": "..."}` body shape that must be updated. |

**Scope_creep_ratio computation:**
```
scope_creep_ratio = files_touched_outside_the_three_above / total_files_touched
```

Where `files_touched` is derived from `git diff --name-only` against the
base commit (`_base-taskflow@1`).

---

## Site_coverage definition

Because a correct implementation can cover all six sites by adding exception
handlers to `app/main.py` without modifying `app/routes/jobs.py`, file-level
coverage would penalise correct implementations. Coverage is therefore defined
by probe results, not by file diffs:

```
site_coverage = (error-site probes that pass) / 8
```

The eight error-site probes are AC-01 through AC-08 in `acceptance.md`.
Each probe exercises one distinct error-triggering scenario. Stage 2 writes
this ratio to `verdict.family_outcome.site_coverage`.

---

## Staleness policy

This file must be regenerated whenever the base version increments. Regenerate
with the command above, re-audit for the framework-level paths, and update the
site table, the frozen total, and the date line.
