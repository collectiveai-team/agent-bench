# L-taskflow

## Identity

| Field | Value |
|---|---|
| Family | L |
| Version | 1 |
| Expected duration | 2–6 h |
| Expected cost | $15–60 |
| Acceptance item count | 37 |

## What it measures

End-to-end capability on a medium-scale greenfield Python service: the solver must plan and implement a layered FastAPI + SQLite + Prefect + WebSocket application from an empty tree, making architectural decisions across five incremental features while keeping all prior tests green. Concrete skills distinguished: layered service design (routes → services → repositories), async SQLAlchemy 2.0 idiom, Prefect v3 flow and task composition with a dispatcher abstraction, bounded in-process event-bus fanout, WebSocket lifecycle management, SQL aggregate queries, and progressive test coverage including sad paths, pagination edge cases, and the full WebSocket event sequence. The case also measures how cleanly a solver navigates accumulating scope: each feature extends shared state (database schema, event bus, dispatcher) without breaking earlier-feature consumers.

## What this case does NOT measure

Context retention across sessions — the solver starts from a clean tree and a single session is the expected delivery unit; any continuity advantage disappears in this design. Defect detection in existing code — there is no pre-existing codebase and no seeded bugs; `B-sabotage` is the correct case for detection hypotheses. Navigation of an unfamiliar codebase — this case starts from an empty tree, so codebase orientation cost is zero; `R-envelope` measures the corresponding cost on a sealed site list.

## Gates

Both commands must exit 0 before any evaluation proceeds:

```sh
uv run ruff check .
uv run pytest -q
```

These gates are identical for all cases and enforced by Stage 2 of the evaluator. No additional gates are permitted.

## Provenance

Ported from `orquesta-lite/benchmark/` (path: `/Users/lionelchamorro/Projects/personal/orquesta-lite/benchmark/`). The source material is copied, not moved; the originating repository retains its own copies. The prior benchmark round (round 4, GPT solution) used this same `features.md` and `CONVENTIONS.md` to produce a scored implementation; round 4 probe pass rate was 14/14. Author: Lionel Chamorro (lio@collectiveai.io). Ported 2026-08-08 as part of the agent-bench build plan.

Version history:
- v1 (2026-08-08): initial port.

## Validity threat: a public reference implementation exists

`cases/_base-taskflow/` in this same public repository is a complete, working implementation of this case's specification, kept because families B and R need a realistic codebase. It is a copyable answer key for `L-taskflow`. This does not distort a comparison — every arm has identical access to it — but it does expose the case to training-data contamination over time. Any round on this case whose result will be published or used to justify spend must run against a private probe overlay, per `references/reporting.md`.
