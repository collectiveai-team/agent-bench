# S-ledger

## Identity

| Field | Value |
|---|---|
| Family | S |
| Version | 1 |
| Expected duration | 15–45 min |
| Expected cost | $1–4 |
| Acceptance item count | 27 |

## What it measures

Short-form greenfield capability on a precision-critical HTTP service: idempotency key handling (exact-once semantics with same-body replay → 200 / same id / no double-debit and different-body replay → 409), boundary math on integer minor-unit balances (no floats anywhere in the money path, atomic debit + credit, balance invariant preserved on failed transfers), and structured error response bodies (400 for missing application-layer header, 404 for unknown accounts, 409 with a discriminating `detail` field, 422 for validation errors). The short scope — approximately 200 LOC of application code — means a solver's probe pass rate reflects these specific behaviors rather than planning or architectural breadth. The case is cheap enough (15–45 min, $1–4) to run at N ≥ 5 in a single session, which makes the decision rule from `references/scoring.md` more reliable when comparing two arms.

## What this case does NOT measure

**Background processing** — there is no worker, no queue, and no background task; a good score here says nothing about Prefect, Celery, or any async dispatch pattern.

**WebSockets** — there is no streaming or push endpoint; the service is purely request-response.

**Cross-session context** — the solver starts from an empty tree and a single session is the expected delivery unit; any continuity advantage disappears in this design. `M-relay` is the correct case for memory or context-retention hypotheses.

**Defect detection in existing code** — there is no pre-existing codebase and no seeded bugs; `B-sabotage` is the correct case for detection hypotheses.

**Codebase navigation** — this case starts from an empty tree, so codebase-orientation cost is zero; `R-envelope` measures the corresponding cost on a sealed site list.

## Gates

Both commands must exit 0 before any evaluation proceeds:

```sh
uv run ruff check .
uv run pytest -q
```

These gates are identical for all cases and enforced by Stage 2 of the evaluator. No additional gates are permitted.

## Provenance

New case, authored from scratch 2026-08-08. Not ported from any prior benchmark round. The spec is derived from a common fintech exercise (ledger + idempotency keys) that recurs across agent benchmarks; the specific contract and probe set are original. Author: Lionel Chamorro (lio@collectiveai.io).

Version history:
- v1 (2026-08-08): initial authoring. Probe validation: 12/12 pass on correct reference; 2/12 fail (test_idempotent_replay_same_body_returns_same_id_and_moves_once and test_idempotent_replay_different_body_conflicts) when idempotency key check is removed.
