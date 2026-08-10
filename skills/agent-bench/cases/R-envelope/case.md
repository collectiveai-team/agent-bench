# R-envelope

## Identity

| Field | Value |
|---|---|
| Family | R |
| Version | 1 |
| Expected duration | 30–90 min |
| Expected cost | $2–8 |
| Acceptance item count | 11 |
| Sealed sites | 6 envelope + 14 propagation |

## What it measures

**Codebase navigation, sweep completeness, and cross-layer refactor
discipline on a realistic service.** The solver receives the
`_base-taskflow@1` service — a FastAPI + SQLite + Prefect job-execution
service with 44 passing tests — and must execute two interlocked halves:

1. **Envelope half.** Migrate every error response to the RFC 7807 Problem
   Details envelope (`application/problem+json` with `type`, `title`,
   `status`, `detail`, and `instance`) without changing any success response
   or breaking the existing suite.

2. **Propagation half.** Add a `RequestContext` (containing a `request_id`
   UUID) that is created once per HTTP request and propagated **explicitly as
   a parameter** through the service and repository layers, appearing in every
   event published to the event bus from an HTTP request. Use of `contextvars`
   or module-level globals is explicitly forbidden.

Scores distinguish solvers that:

- locate every error-producing code path in an unfamiliar codebase (including
  both application-level `HTTPException` raises and framework-level
  `RequestValidationError` paths that require a custom handler override);
- execute a complete cross-layer sweep (propagation sealed files:
  `app/services/jobs.py`, `app/repositories/jobs.py`, `app/events.py`);
- make a correct, minimal change — adding exception handlers that cover all
  paths rather than editing each raise site individually;
- thread context explicitly without reaching for ambient state;
- update the subset of existing tests that assert the old error shape, without
  touching success-path tests.

This is the case where **subagent strategies should separate from
single-session ones**. A single-session solver must hold the full codebase
map in context while tracking which sites have been migrated and which
remain. A subagent strategy can delegate the site-discovery pass to one
agent, the migration to another, and the test-update pass to a third, keeping
each context window focused. Coverage gaps caused by context loss show up
directly in site_coverage.

## What this case does NOT measure

**Greenfield design** — the solver modifies an existing service, not designs
a new one. A good score here says nothing about API contract choices, database
schema design, or service architecture.

**Defect detection** — there are no seeded bugs and no bug-hunting task.
`B-sabotage` is the correct case for defect-detection hypotheses.

**Cross-session context** — the task is completed in a single session starting
from the base tree. No prior session state is required or relevant. `M-relay`
is the correct case for memory or context-retention hypotheses.

**Long-horizon planning** — the task scope is bounded by the two sealed site
lists. Long-form planning or multi-day orchestration skills are not exercised.

## Gates

Both commands must exit 0 before any evaluation proceeds:

```sh
uv run ruff check .
uv run pytest -q
```

These gates are identical for all cases and enforced by Stage 2 of the
evaluator. No additional gates are permitted.

## Provenance

New case, authored 2026-08-10. Based on `_base-taskflow@1` (frozen
2026-08-08), which is a complete implementation of the `L-taskflow`
specification. The envelope half is derived from the RFC 7807 (Problem
Details for HTTP APIs) standard. The propagation half is derived from
the request-scoped context pattern common in FastAPI services. Author: Lionel
Chamorro.

Version history:
- v1 (2026-08-10): initial authoring. Six envelope sites sealed. Probe
  validation: 10/10 pass on full migration reference; 1/10 fail
  (`test_unhandled_exception_500_is_problem_json`) when the `Exception`
  handler is removed. Base suite remains 44/44 throughout.
- v2 (2026-08-10): added propagation half (14 sealed propagation sites across
  3 files). Probe count rises to 11. Duration revised to 30–90 min / $2–8 to
  reflect broader scope. site_coverage redefined to file-based propagation
  coverage (3 sealed files). Scope_creep rule made deterministic. instance
  constraint tightened to assert startswith("/").
