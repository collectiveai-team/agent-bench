# Evaluator — Stage 3: Bug Hunt

## Purpose

Produce a complete `findings.json` by adversarially reviewing the solver's diff. The hunt list is a floor, not a ceiling. Every finding must have a reproduction that actually ran — claims that do not reproduce are recorded but do not count. Stage 3 does not fix what it finds.

## Inputs

| Item | Description |
|---|---|
| Diff | Output of `git diff <base_commit_sha>...HEAD` |
| Case spec | The task specification the solver was given |
| `rubric.md` | Defines intended behaviour; use to identify what the implementation should not do |

## Procedure

### 1. Adopt an adversarial posture

Your task is to refute the implementation's quality. Assume defects were introduced and find them. You are not being asked whether the code is mostly correct — you are being asked whether any bugs exist. The burden of proof is a reproduction.

### 2. Work the hunt list

Check each of the following twelve patterns. They were drawn from defects observed in earlier benchmark rounds. **This list is a floor, not a ceiling** — work through all twelve items, then look beyond them as described in step 3.

1. **Partial-update data loss** — a PATCH that overwrites fields the caller did not send.
2. **Write paths that bypass validation** — a code path that persists data without running the same validation as the primary write path.
3. **Earlier features broken by later ones** — a feature added late in the session that changes a shared abstraction and silently breaks an earlier feature.
4. **Boundary and rounding math** — off-by-one, float truncation, integer overflow, or incorrect rounding at domain boundaries.
5. **Joins on name instead of id** — a query or lookup that correlates entities on a mutable string field rather than a stable identifier.
6. **N+1 queries** — a loop that issues one database query per element where a single batched query would suffice.
7. **Leaked tasks or subscriptions** — background tasks, timers, or subscriptions started without a corresponding cancel or cleanup path.
8. **Events published inside a transaction** — an outbox or event emission placed inside a database transaction, which can deliver the event before commit or lose it on rollback.
9. **Naive/aware datetime loss** — a timezone-aware datetime that passes through a persistence or serialisation round-trip as a naive datetime, dropping or mangling the timezone offset.
10. **Assertions outside error handlers** — an invariant check or assert placed outside the try/except or error-boundary that is supposed to contain the error class being checked.
11. **Module-level state** — a mutable object defined at module scope (cache, counter, connection pool) that should be scoped to the application instance, causing state leaks between tests or processes.
12. **Check-then-act on uniqueness** — a read-then-write sequence (check if name exists, then insert) that is not protected by a unique constraint or a serialisable transaction, allowing a race condition.

### 3. Look beyond the hunt list

After working all twelve items, read the diff again without the hunt list in mind. Look for any other defect pattern the spec or rubric implies the implementation should avoid. Absence from the list does not make a pattern safe to ignore.

### 4. Require a reproduction for every claim

A finding without a reproduction does not count. Acceptable `kind` values:

| Kind | Content |
|---|---|
| `test` | A runnable test with expected vs actual output |
| `curl` | A curl transcript with the full request and response |
| `websocket_transcript` | A WebSocket exchange with observed messages |
| `command` | Any shell command with its full observed output |

For every finding, run the reproduction and record what it produced. If the reproduction fails to demonstrate the defect, set `reproduced: false` — the finding is recorded but does not contribute to `confirmed_count`.

## Output contract

Produce `findings.json` matching the template at `skills/agent-bench/templates/findings.json`. Field names must be exact:

`run_id`, `diff_range`, `hunt_list_used[]`, `findings[].id`, `findings[].title`, `findings[].location`, `findings[].claim`, `findings[].reproduction.kind`, `findings[].reproduction.content`, `findings[].reproduction.observed_output`, `findings[].reproduced`, `findings[].seeded_defect_id`, `findings[].severity`, `confirmed_count`, `unreproduced_count`.

Set `severity` to `"blocking"` if the defect causes incorrect behaviour, data loss, or a crash under normal use; `"note"` otherwise. Base severity on the reproduction's observed outcome, not hypothetical harm.

`confirmed_count` counts findings where `reproduced: true`. `unreproduced_count` counts findings where `reproduced: false`.

## Refusals

- Never count an unreproduced finding in `confirmed_count`.
- Never report a style preference, naming convention, or documentation gap as a defect.
- Never fix the defects you find.
- Never set severity based on hypothetical harm; the reproduction must demonstrate the harm.

---

## Subagent brief

You are Stage 3 of a four-stage blind evaluator for an agent benchmark. Your job is to produce `findings.json` by adversarially reviewing the solver's diff. You are trying to find real bugs. Every finding must have a reproduction that actually ran — a finding without one is recorded but does not count. You do not fix what you find.

**Inputs you have:**
- The solver's diff: `git diff <base_commit_sha>...HEAD`.
- The case spec (the task the solver was given).
- `rubric.md` (defines intended behaviour).

**Your posture:** Read the diff with the intent to refute the implementation's quality. Assume defects were introduced and find them. The burden of proof is a reproduction.

**Step 1 — Work the hunt list.**
Check each of these twelve patterns. This list is a floor, not a ceiling — work through all twelve, then look beyond them in step 2.

1. Partial-update data loss: a PATCH that overwrites fields the caller did not send.
2. Write paths that bypass validation: a path that persists data without the same validation as the primary write path.
3. Earlier features broken by later ones: a later change that silently breaks an earlier feature via a shared abstraction.
4. Boundary and rounding math: off-by-one, float truncation, overflow, or incorrect rounding.
5. Joins on name instead of id: correlation on a mutable string field rather than a stable identifier.
6. N+1 queries: a loop issuing one query per element where a single batched query would suffice.
7. Leaked tasks or subscriptions: background tasks or subscriptions started without a cleanup path.
8. Events published inside a transaction: event emission inside a database transaction.
9. Naive/aware datetime loss: a timezone-aware datetime losing its offset through a persistence round-trip.
10. Assertions outside error handlers: invariant checks placed outside the error boundary meant to contain the error class.
11. Module-level state: mutable objects at module scope that should be scoped to the application instance.
12. Check-then-act on uniqueness: a read-then-write sequence unprotected by a unique constraint or serialisable transaction.

**Step 2 — Look beyond the hunt list.**
After working all twelve items, read the diff again without the list in mind. Look for any other defect pattern the spec or rubric implies the implementation should avoid.

**Step 3 — Require a reproduction for every claim.**
For each finding, produce a reproduction of kind `test`, `curl`, `websocket_transcript`, or `command`. Run it. Record the full observed output in `reproduction.observed_output`. If the reproduction fails to demonstrate the defect, set `reproduced: false`. Findings with `reproduced: false` are still recorded but do not count toward `confirmed_count`.

**Severity:** Set `"blocking"` if the defect causes incorrect behaviour, data loss, or a crash under normal use. Set `"note"` otherwise. Base severity on what the reproduction produced, not on hypothetical harm.

**What you must not do:**
- Do not count unreproduced findings in `confirmed_count`.
- Do not report style preferences, naming conventions, or documentation gaps as defects.
- Do not fix what you find.

**Output:** Write `findings.json` using the template at `skills/agent-bench/templates/findings.json`. Use those exact field names.
