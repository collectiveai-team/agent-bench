# M-relay

## Identity

| Field | Value |
|---|---|
| Family | M |
| Version | 1 |
| Expected duration | 1–2 h (total across three sessions) |
| Expected cost | $4–12 |
| Acceptance item count | 27 |
| Legs | 3 |

## What it measures

**Cross-session continuity on a precision-critical HTTP service.** The solver builds the same
service as `S-ledger` (accounts with integer minor-unit balances, idempotency-key-protected
transfers, paginated transaction history) but delivers it across three cold sessions. The
case measures whether a solver maintains consistent design decisions — field names, ID
scheme, error body format, timestamp representation — across session boundaries where
conversation state is not available.

The primary signals are:
- `continuity`: share of leg-1 design decisions that are still correctly honoured at the
  end of leg 3 (verified by the sealed `continuity.md` checklist).
- `rework_ratio`: share of already-delivered code rewritten in later legs (measured from
  git diffs at leg boundaries), which reflects how much the solver had to backtrack when
  continuity broke down.
- `final_outcome`: the full S-ledger correctness formula applied to the leg-3 result,
  confirming that cross-session delivery reached the same functional endpoint as a
  single-session run.

The case is specifically designed to produce signal for memory-mechanism comparisons (see
`## Required arm structure`). It cannot produce that signal for single-session runs.

## What this case does NOT measure

**Greenfield scale** — the contract is identical to `S-ledger` (~200 LOC of application
code); this case adds cross-session friction, not scope. A good `M-relay` score says nothing
about a solver's ability to plan or implement larger greenfield systems.

**Defect detection** — there are no seeded bugs and no bug-hunting task. `B-sabotage` is
the correct case for defect-detection hypotheses.

**Codebase navigation** — each leg starts from a known checkpoint with the solver's own
prior code. The session boundary adds cold-context cost, not unfamiliar-codebase cost.
`R-envelope` measures codebase navigation cost on a sealed site list.

**Single-session correctness discrimination** — both memory arms converge to the same final
contract; the discriminating signals are continuity and rework, not the final probe pass
rate alone. An arm with poor continuity but heavy rework can still pass all probes.

## Gates

Both commands must exit 0 before any evaluation proceeds:

```sh
uv run ruff check .
uv run pytest -q
```

These gates are identical for all cases and enforced by Stage 2 of the evaluator. No
additional gates are permitted.

## Required arm structure

A memory-mechanism comparison using this case must satisfy the following structure. Any
deviation invalidates the comparison.

**One independent variable.** Only the memory mechanism may differ between arms. All other
elements — agent binary, model, prompt, tool permissions, case version, scaffold commit,
machine — must be byte-identical and hashed in `manifest.held_constant` and
`manifest.solver.config_files`.

**Example valid comparison:** memory MCP server enabled vs. disabled. The arm with memory
MCP has the server configured and running; the arm without it does not. Every other
parameter (model, prompt, tool permissions, harness version, leg specs) is identical.

**Cold context enforcement.** At each leg boundary, the harness must:
1. End the current agent session (destroy the conversation state / message history).
2. Start a fresh agent session with no in-context memory from the prior session.
3. Provide the fresh session with only the leg spec for the current leg and the repository
   at its current HEAD.

What must NOT carry across a leg boundary: conversation state (message history, in-context
information from the prior session).

What MAY carry across a leg boundary: the repository (all committed files and history), and
whatever persistence the arm under test provides. The persistence mechanism is the
independent variable — it is what the comparison is testing.

**Identical leg prompts.** Both arms receive the identical text of `spec/leg-1.md`,
`spec/leg-2.md`, and `spec/leg-3.md` respectively, with no additional context injected.
Any extra context (e.g. "here is your memory from last time:") must be delivered
exclusively through the arm's configured persistence mechanism, not by modifying the
prompt.

**Identical cold-context handling.** Both arms must receive the same repository state at the
start of each leg. Neither arm may receive a summary or transcript of the prior session
injected into the prompt. The only difference is whether the solver's persistence mechanism
(memory MCP, notes files, etc.) contains information from prior legs.

## Provenance

New case, authored 2026-08-10. Not ported from any prior benchmark round. The contract is
identical to `S-ledger` (Task 12), split into three cold sessions. The probe is the
unmodified S-ledger probe (byte-identical; see `probes/VALIDATION.md`). Author: Lionel
Chamorro.

Version history:
- v1 (2026-08-10): initial authoring. Probe validation inherited by byte-identity from
  S-ledger (12/12 pass on full contract; 2/12 fail when idempotency key check removed).
  Continuity checklist: 7 rows. Acceptance: 27 items (identical to S-ledger).
