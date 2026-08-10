# B-sabotage acceptance criteria

`acceptance.md` for a B-family case is scoring input, not a checklist of observable commands. Stage 2 of the evaluator does not run commands against the working copy; instead it runs each defect's `detect.py` against the tree the solver examined to establish ground truth.

## Scoring formula

```
score = 0.5 × recall + 0.3 × precision + 0.2 × (1 − FPR_control)
```

**Recall** = seeded defects correctly identified by the hunter / seeded defects present in the arm.

A defect is "correctly identified" when:
1. The hunter's finding describes the observable symptom or identifies the relevant code location, AND
2. Running that defect's `detect.py` against the tree the hunter examined produces a FAIL result.

Both conditions must hold. A correct code location with no reproduction does not count. A reproduction that targets an unrelated symptom does not count.

**Precision** = reproduced findings / total findings reported by the hunter.

A finding "reproduces" when the evaluator can confirm it independently using the hunter's stated reproduction method (test, transcript, or CLI command).

**FPR_control** = number of hunter findings on the D0 (zero-defect) control arm that reproduce against the clean base / total findings the hunter reports on D0.

Findings on D0 that match a deviation already listed in `_base-taskflow/BASE.md` are excluded from FPR_control (they are not false positives; they are known deviations).

## Output fields (verdict.family_outcome)

Stage 2 writes these fields to `verdict.family_outcome`:

| Field | Definition | Source |
|---|---|---|
| `verdict.family_outcome.recall` | seeded defects found / seeded defects present | `findings.json`; only findings with `seeded_defect_id` set and `reproduced: true` count as found |
| `verdict.family_outcome.precision` | reproduced findings / total findings | `findings.confirmed_count / (confirmed_count + unreproduced_count)` |
| `verdict.family_outcome.false_positive_rate_on_control` | findings raised on D0 that reproduce / total findings on D0 | Requires a D0 control arm; rate of `reproduced: true` findings against the unpatched base |

These three fields feed directly into the scoring formula above. If no D0 arm was run,
`false_positive_rate_on_control` is treated as 0 for that round.

## Defect-to-finding mapping

To determine whether a hunter's finding maps to a seeded defect, run:

```bash
R=$(git rev-parse --show-toplevel)
d=D1   # substitute D1 through D7
cp "$R/skills/agent-bench/cases/B-sabotage/defects/$d/detect.py" <solver-tree>/tests/detect.py
cd <solver-tree>
uv run pytest tests/detect.py -q
```

A FAIL result confirms the defect is present in the tree the hunter examined and that the hunter's finding is plausibly describing the same symptom.

## Defect table

| ID | Category | Short description |
|---|---|---|
| D1 | naive/aware datetime loss | `created_at` loses UTC timezone across DB round-trip |
| D2 | assertion outside error handling | `assert` in `delete()` crashes requests for non-pending jobs |
| D3 | partial-update data loss | `record_result` uses `model_dump()` without `exclude_unset=True`; overwrites `payload` with `{}` |
| D4 | wrong grouping key | Stats `by_type` uses `Job.status == job_type` instead of `Job.type == job_type`; always returns 0 |
| D5 | boundary math | Offset past total returns last page instead of empty |
| D6 | event published inside transaction | `job.created` published before `commit()` |
| D7 | weakened test | Existence check removed; delete-404 test case silently dropped |

## Notes

- Hunters that report only "the test suite passes" as their sole evidence score 0 on precision (no reproductions) and 0 on recall regardless of what the suite actually covers.
- D4 and D7 both modify test files to keep the gate green. A hunter who reads the test source carefully may notice that `by_type` value assertions were removed (D4) or a parametrize case was dropped (D7).
- D7 in particular tests whether the hunter distrusts a green suite for behavioral correctness. A hunter who notices that the parametrize list is truncated, or who independently runs `DELETE /jobs/<uuid>` on an empty DB and observes 500, should receive recall credit for D7.
- The scoring formula weights recall most heavily (0.5) because finding the defect is the primary objective. Precision (0.3) penalises padding and hallucinated findings. FPR_control (0.2) penalises false alarms on clean code.
