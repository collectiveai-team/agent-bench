# B-sabotage

## Identity

| Field | Value |
|---|---|
| Family | B |
| Version | 1 |
| Expected duration | 20–60 min |
| Expected cost | $1–5 |
| Seeded defects | 7 (D1–D7) |
| Control arm | D0 (zero-defect) |

## What it measures

**Defect detection and evidence quality in an existing codebase.** The solver receives the `_base-taskflow@1` service with zero or more defect patches applied and is asked to find and reproduce every violation of the service's documented behaviour. Scores distinguish solvers that:

- find most seeded defects (recall) from those that find few;
- report only reproducible findings (precision) from those that pad with speculation;
- remain sceptical of a green test suite (D7 specifically tests this) from those that treat green gates as proof of correctness;
- produce actionable, well-evidenced reports from those that produce superficial ones.

The seven seeded defects span six defect pattern categories documented in `references/evaluator-3-bughunt.md`: naive/aware datetime loss, assertion outside error handling, partial-update data loss, wrong-column filter, boundary math, event ordering, and weakened test.

## What this case does NOT measure

**Authoring ability** — the solver writes no production code. A good score here says nothing about greenfield design, API contract choices, or test coverage planning.

**Architecture** — the service architecture is fixed. The solver cannot change the layering, the framework, or the persistence strategy.

**Cross-session context** — the audit starts from a complete, self-contained tree. Memory of prior sessions provides no structural advantage. `M-relay` is the correct case for memory or context-retention hypotheses.

**Greenfield correctness** — the solver is not asked to build anything. `S-ledger`, `S-ingest`, and the L-family are the correct cases for build-from-scratch hypotheses.

## Gates

Both commands must exit 0 before any evaluation proceeds:

```sh
uv run ruff check .
uv run pytest -q
```

These gates are identical for all cases and enforced by Stage 2 of the evaluator.

## Provenance

New case, authored 2026-08-08. Based on `_base-taskflow@1` (frozen 2026-08-08), which is a complete implementation of the `L-taskflow` specification. The seven defect patterns were selected from the hunt-list in `references/evaluator-3-bughunt.md`. Author: Lionel Chamorro (lio@collectiveai.io).

Version history:
- v1 (2026-08-08): initial authoring. Seven defects (D1–D7) verified: each patch.diff applies cleanly, keeps both gates green, and is caught by its detect.py. All seven detectors confirmed to pass on the clean D0 base.
