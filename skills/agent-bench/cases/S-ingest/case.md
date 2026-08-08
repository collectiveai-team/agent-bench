# S-ingest

## Identity

| Field | Value |
|---|---|
| Family | S |
| Version | 1 |
| Expected duration | 15–45 min |
| Expected cost | $1–4 |
| Acceptance item count | 22 |

## What it measures

Short-form greenfield capability on a CLI rather than an HTTP service:
schema-driven row validation with a defined rule-evaluation order (id
non-empty → id unique → amount_minor integer → currency three-uppercase-letters
→ occurred_at timezone-aware), quarantine output fidelity (original columns
preserved plus a correct `reason` column naming only the first failing rule),
exit-code precedence when multiple conditions apply (`--strict` overrides
valid/invalid determination; missing file always exits 2), and exact
stdout-summary formatting (`read=N valid=N quarantined=N`). The short scope —
approximately 100–150 LOC of application code — means a solver's probe pass
rate reflects these specific behaviours rather than planning or architectural
breadth. The case is cheap enough (15–45 min, $1–4) to run at N ≥ 5 in a
single session, and its non-HTTP shape makes it a useful complement to
`S-ledger` when the hypothesis concerns CLI design or stream-processing
patterns rather than REST semantics.

## What this case does NOT measure

**HTTP contract design** — there is no server, no endpoint, and no HTTP surface;
a good score here says nothing about route design, status codes, or request
validation via Pydantic body schemas.

**Persistence and state across invocations** — each CLI run reads one input
file and writes two output files; there is no database, no migration, and no
state shared between invocations.

**Background work** — there is no worker, no queue, no async task, and no
event loop; all processing is single-threaded and synchronous within a single
process lifetime.

**Cross-session context** — the solver starts from an empty tree and a single
session is the expected delivery unit; any continuity advantage disappears in
this design. `M-relay` is the correct case for memory or context-retention
hypotheses.

**Defect detection in existing code** — there is no pre-existing codebase and
no seeded bugs; `B-sabotage` is the correct case for detection hypotheses.

**Codebase navigation** — this case starts from an empty tree, so
codebase-orientation cost is zero; `R-envelope` measures the corresponding
cost on a sealed site list.

## Gates

Both commands must exit 0 before any evaluation proceeds:

```sh
uv run ruff check .
uv run pytest -q
```

These gates are identical for all cases and enforced by Stage 2 of the
evaluator. No additional gates are permitted.

## Provenance

New case, authored from scratch 2026-08-08. Not ported from any prior
benchmark round. The spec is derived from a common data-engineering exercise
(schema-validating ingest pipeline with quarantine) that recurs in analytics
and data-platform interview settings; the specific CLI contract, exit-code
precedence table, and probe set are original. Author: Lionel Chamorro
(lio@collectiveai.io).

Version history:
- v1 (2026-08-08): initial authoring. Probe validation: 8/8 pass on correct
  reference; 1/8 fail (`test_duplicate_id_quarantines_the_later_row`) when
  duplicate-id detection is commented out.
