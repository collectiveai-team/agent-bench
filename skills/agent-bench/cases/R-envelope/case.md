# R-envelope

## Identity

| Field | Value |
|---|---|
| Family | R |
| Version | 1 |
| Expected duration | 20–60 min |
| Expected cost | $1–5 |
| Acceptance item count | 10 |
| Sealed sites | 6 |

## What it measures

**Codebase navigation and sweep completeness on a realistic service.** The
solver receives the `_base-taskflow@1` service — a FastAPI + SQLite + Prefect
job-execution service with 44 passing tests — and must migrate every error
response to the RFC 7807 Problem Details envelope (`application/problem+json`
with `type`, `title`, `status`, `detail`, and `instance`) without changing
any success response and without breaking the existing suite.

Scores distinguish solvers that:

- locate every error-producing code path in an unfamiliar codebase (including
  both application-level `HTTPException` raises and framework-level
  `RequestValidationError` paths that require a custom handler override);
- execute a complete sweep (site_coverage across six sealed sites);
- make a correct, minimal change — adding exception handlers that cover all
  paths rather than editing each raise site individually;
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

**Long-horizon planning** — the task scope is bounded (six sites, three files,
~30–50 LOC of new handler code). Long-form planning or multi-day
orchestration skills are not exercised.

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
specification. The migration task is derived from the RFC 7807 (Problem
Details for HTTP APIs) standard and is a common refactoring pattern in
real-world FastAPI services. Author: Lionel Chamorro.

Version history:
- v1 (2026-08-10): initial authoring. Six sites sealed. Probe validation:
  10/10 pass on full migration reference; 1/10 fail
  (`test_unhandled_exception_500_is_problem_json`) when the `Exception`
  handler is removed. Base suite remains 44/44 throughout.
