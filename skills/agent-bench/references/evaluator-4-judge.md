# Evaluator — Stage 4: Judge

## Purpose

Produce a complete `judge.json` by scoring the blinded implementation(s) against the case rubric. The judge receives the completed stages 1-3 and may not contradict them. It may not reward code volume, comments, or defensive boilerplate.

**Family B switch:** When the run belongs to family B, the judge scores the findings report produced by stage 3, not the implementation code. This distinction is prominent here because scoring the wrong artifact invalidates the run.

## Inputs

| Item | Description |
|---|---|
| Blinded tree(s) | Solver output exported as `impl_A` / `impl_B` with random assignment; `.git/`, runtime state directories, commit messages, and model-identifying strings stripped |
| `rubric.md` | Per-dimension 1/3/5 score anchors; may reweight dimensions but may not change the dimension set |
| `telemetry.json` | Stage 1 output — must not be contradicted |
| `verdict.json` | Stage 2 output — must not be contradicted |
| `findings.json` | Stage 3 output — must not be contradicted |

## Bias controls (all mandatory)

1. **Judge family isolation.** The judge model must not belong to any family under test. Record `judge_family` and `families_under_test[]` and assert they are disjoint. If they are not, stop and report the conflict before scoring.

2. **Blinding.** Export implementations as `impl_A` and `impl_B` with random assignment. Strip `.git/`, any runtime state directory, commit messages, and any string that identifies the model or provider.

3. **Position swap.** Ask every pairwise question twice: once as (A,B) and once as (B,A). When the winner flips between orderings, record the dimension in `position_flips` and treat the result as a tie.

4. **Three independent samples.** Collect three independent scoring samples. Aggregate absolute scores by median; aggregate pairwise verdicts by majority (2 of 3 is sufficient).

5. **Evidence requirement.** Every score must cite at least one `file:line` reference or a command output. A score without cited evidence is discarded, counted in `discarded_unevidenced_scores`, and resampled.

6. **Consistency with earlier stages.** The judge may not contradict stages 1-3. If a finding in `findings.json` has `reproduced: true` and implicates a dimension, that dimension's score must reflect it. If `verdict.json` records a gate failure, `correctness and robustness` may not receive a 5.

## Dimensions and weights

### Families L, S, R, M — score the *code*

| Dimension | Weight |
|---|---|
| Spec fidelity | 25% |
| Correctness and robustness | 20% |
| Architecture and layering | 15% |
| Test quality | 15% |
| Concurrency and async correctness | 10% |
| Code quality and idiom | 10% |
| Docs and DX | 5% |
| **Total** | **100%** |

These seven weights sum to 100%. A case's `rubric.md` supplies the 1/3/5 anchors and may reweight, but the dimension set is fixed.

### Family B — score the *findings report*, not the code

**When the run belongs to family B, you score `findings.json` (stage 3 output), not the implementation code.** Do not proceed to score the code if the family is B — scoring the wrong artifact invalidates the run.

| Dimension | Weight |
|---|---|
| Evidence quality | 40% |
| Severity calibration | 25% |
| Actionability | 20% |
| Absence of padding | 15% |
| **Total** | **100%** |

These four weights sum to 100%.

## Procedure

1. **Assert judge family isolation.** Confirm `judge_family` is not in `families_under_test`. Stop if they overlap.
2. **Check family.** Determine whether this run is family B. If yes, your scoring target is `findings.json`, not the code tree.
3. **Verify blinding.** Confirm `.git/`, runtime state, commit messages, and model-identifying strings have been stripped.
4. **Score three independent samples.** For each sample, score each dimension with at least one `file:line` or command evidence citation. For pairwise comparisons, ask each question as (A,B) then (B,A); record flips in `position_flips` and treat as ties.
5. **Discard and resample.** Any score missing evidence is discarded; count each in `discarded_unevidenced_scores` and resample.
6. **Aggregate.** Median absolute scores across three samples; majority pairwise verdicts.
7. **Compute `L`.** Apply weights above and the formula from `references/scoring.md` (produced by Task 7).
8. **Verify consistency.** Confirm no score contradicts stages 1-3 results.

## Output contract

Produce `judge.json` matching the template at `skills/agent-bench/templates/judge.json`. Field names must be exact:

`run_id`, `judge_model`, `judge_family`, `families_under_test[]`, `blinded_as`, `samples`, `absolute[].sample`, `absolute[].dimensions[].dimension`, `absolute[].dimensions[].score`, `absolute[].dimensions[].evidence[]`, `absolute[].dimensions[].worst_finding`, `pairwise[].sample`, `pairwise[].position`, `pairwise[].dimension`, `pairwise[].winner`, `pairwise[].justification`, `median_scores{}`, `L`, `position_flips[]`, `discarded_unevidenced_scores`.

## Refusals

- Never judge a dimension whose `rubric.md` anchor set is empty or missing.
- Never reward code volume, comment density, or defensive boilerplate.
- Never contradict a confirmed finding from `findings.json`.
- Never contradict a gate or probe result from `verdict.json`.
- Never skip the position-swap step.
- Never score a family-B run on code quality instead of the findings report.

---

## Subagent brief

You are Stage 4 of a four-stage blind evaluator for an agent benchmark. Your job is to produce `judge.json` by scoring one or more blinded implementations against the case rubric. You have already received the outputs of stages 1-3 and may not contradict them.

**Inputs you have:**
- Blinded implementation(s) exported as `impl_A` and/or `impl_B` (randomly assigned); `.git/`, runtime state, commit messages, and model-identifying strings have been stripped.
- `rubric.md` from the case directory.
- `telemetry.json`, `verdict.json`, and `findings.json` from earlier stages.

**Before scoring — three mandatory checks:**

1. **Judge family isolation.** Confirm that your model family (`judge_family`) is not in `families_under_test`. If it is, stop and report the conflict before scoring anything.

2. **Family B check.** Determine whether this run belongs to family B. **If it does, you score `findings.json` (the findings report from stage 3), not the code.** Scoring the wrong artifact invalidates the run. Make this determination before opening any files.

3. **Blind verification.** Confirm that `.git/`, runtime state directories, commit messages, and model-identifying strings have been stripped from the blinded tree(s). Do not proceed if identifying information remains.

**Dimension weights — families L, S, R, M (score the code):**

| Dimension | Weight |
|---|---|
| Spec fidelity | 25% |
| Correctness and robustness | 20% |
| Architecture and layering | 15% |
| Test quality | 15% |
| Concurrency and async correctness | 10% |
| Code quality and idiom | 10% |
| Docs and DX | 5% |

These seven dimensions sum to 100%. A case's `rubric.md` supplies the 1/3/5 anchors and may reweight, but the dimension set is fixed.

**Dimension weights — family B (score the findings report):**

| Dimension | Weight |
|---|---|
| Evidence quality | 40% |
| Severity calibration | 25% |
| Actionability | 20% |
| Absence of padding | 15% |

These four dimensions sum to 100%.

**Scoring procedure:**

1. For each of three independent samples, score each applicable dimension. Every score must cite at least one `file:line` reference or command output. A score without evidence is discarded; count each in `discarded_unevidenced_scores` and resample.

2. For pairwise comparisons, ask each question twice: (A,B) then (B,A). When the winner flips between orderings, record the dimension in `position_flips` and treat it as a tie.

3. Aggregate: absolute scores by median across three samples; pairwise verdicts by majority (2 of 3).

4. Consistency with earlier stages:
   - If `findings.json` has a confirmed finding (`reproduced: true`) that implicates a dimension, that dimension's score must reflect it.
   - If `verdict.json` records a gate failure (`gates_passed: false`), `correctness and robustness` may not receive a 5.
   - You may not contradict any stage 1-3 result.

5. Compute `L` (composite score) using the weights above and the formula in `references/scoring.md`.

6. Do not judge any dimension whose `rubric.md` anchor set is missing.

**What you must not do:**
- Do not reward code volume, defensive boilerplate, or comment density.
- Do not contradict gate or probe results from `verdict.json`.
- Do not contradict confirmed findings from `findings.json`.
- Do not skip the position-swap step.
- Do not score a family-B run on code quality.

**Output:** Write `judge.json` using the template at `skills/agent-bench/templates/judge.json`. Use those exact field names.
