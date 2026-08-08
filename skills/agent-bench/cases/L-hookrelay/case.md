# L-hookrelay

## Identity

| Field | Value |
|---|---|
| Family | L |
| Version | 1 |
| Expected duration | 2–6 h |
| Expected cost | $15–60 |
| Acceptance item count | 42 |

## What it measures

End-to-end capability on a medium-scale greenfield Python service: the solver must plan and implement a layered FastAPI + SQLite + async HTTP + SSE application from an empty tree, making architectural decisions across six incremental features while keeping all prior tests green. Concrete skills distinguished: layered service design (routes → services → repositories), async SQLAlchemy 2.0 idiom, a background delivery dispatcher with bounded concurrency, exponential-backoff retries, and HMAC-SHA256 request signing, an in-process status bus with bounded queues and subscriber lifecycle management, SSE streaming with correct disconnect cleanup, graceful shutdown with no stuck `sending` rows and resumption from a reverted delivery, and progressive test coverage including sad paths across all of: retries, dead letters, inactive subscription exclusion, timeouts, disconnects, and shutdown. The case also measures whether the solver designs the delivery-client testability seam (`http.delivery_client_factory`) correctly, since without it the probe suite cannot inject an in-process ASGI receiver and all delivery-dependent tests fail.

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

Ported from `orquesta-lite/benchmark/round2/` (path: `/Users/lionelchamorro/Projects/personal/orquesta-lite/benchmark/round2/`). The source material is copied, not moved; the originating repository retains its own copies. The prior benchmark evaluation (round 4, GPT solution) used this same `features.md` and `CONVENTIONS.md`; round 4 probe pass rate was 15/15 on probe v2.2. Author: Lionel Chamorro (lio@collectiveai.io). Ported 2026-08-08 as part of the agent-bench build plan.

**Acceptance item count: 42 vs. round 4's 30.** Round 4 evaluated at the spec sub-bullet level (each sub-bullet = 1 item, per `evaluation.md` §2). This port applies the same granularity rule as `L-taskflow`: one row per independently falsifiable observable criterion. That yields more rows because status-code checks and body-shape checks are independently falsifiable and split into separate rows; the secret-not-in-response security invariant is isolated as its own row; and the four delivery log `422` cases each have their own row. The count difference is a measurement precision increase, not scope creep. The approach matches the sibling case (`L-taskflow`, 37 items from a spec with a similar sub-bullet count) and produces a consistent signal across rounds.

**Judge anchor provenance:** `evaluation.md` §3.2 states "Anchors as in round 1's §3.2" without reprinting them, so they were adapted from the `L-taskflow` rubric anchors to hookrelay's surface (SSE instead of WebSocket, delivery dispatcher instead of Prefect worker, HMAC signing added as a correctness marker). The dimension set and weights are unchanged.

Version history:
- v1 (2026-08-08): initial port.
