# Reporting reference

> **Scope.** This document defines what a complete run record looks like and what must appear in every report produced from benchmark output. Templates are in `skills/agent-bench/templates/`. Every number in a report must be traceable to a ledger file — no figures from memory or re-computation after the fact.

---

## Per-run report

Fill `skills/agent-bench/templates/report.md` for every run. Every field must resolve to a specific ledger file and field path.

| Report section | Source |
|---|---|
| Convergence | `telemetry.json → convergence` |
| Attempts / retries | `telemetry.json → totals.attempts` |
| Commits | `telemetry.json → process_hygiene.commits` |
| Acceptance | `verdict.json → acceptance.passed_items / acceptance.total_items` |
| Gates | `verdict.json → gates_passed`; detail in `verdict.gates` |
| Hidden probes | `verdict.json → probes.passed / probes.total` |
| Confirmed bugs | `findings.json → confirmed_count` (reproduced findings only) |
| Cost (USD) | `telemetry.json → totals.cost_usd` |
| Cost basis | `telemetry.json → cost_basis` and `cost_basis_note` |
| Token counts | `telemetry.json → totals.input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens` |
| Wall-clock (total / net) | `telemetry.json → totals.wall_clock_seconds` / `wall_clock_seconds_net_of_rate_limits` |
| Cost per outcome point | Computed: `cost_usd / correctness_normalized`; both inputs from ledger files |
| Judge dimension scores | `judge.json → median_scores`, one row per dimension |
| Worst findings | `judge.json → absolute[].dimensions[].worst_finding` |
| `correctness_normalized` | Computed per family formula in `scoring.md`; inputs from `verdict.json` and `findings.json` |
| `efficiency` | Computed per `scoring.md`; inputs `telemetry.totals.cost_usd` and `telemetry.totals.wall_clock_seconds_net_of_rate_limits` |
| `Q`, `L`, Composite | Computed per `scoring.md`; `L` from `judge.json → L` |

`## Threats to validity` in `report.md` is **mandatory**. It may never be omitted and may never be answered "none". See the seed list in `## Threats to validity` below.

---

## Round report

A round report covers all arms of one hypothesis test. It must include:

1. **Winner and margin.** State which arm has the higher median Composite and by how much.
2. **Whether the margin exceeds the within-arm spread.** Apply the decision rule from `scoring.md § Decision rule`. If ranges overlap, write "inconclusive" — not "arm A leads".
3. **Cost split by role.** Table of `telemetry.by_role[].role` vs `cost_usd`, one column per arm. Helps diagnose whether cost differences come from orchestrator, subagent, or tool calls.
4. **Confirmed-bug list.** All findings where `reproduced: true` from `findings.json`, with severity and location, one row per arm.
5. **Judge justifications for the three largest gaps.** For each of the three dimensions where the gap between arm median scores is largest, quote the justification from `judge.json → pairwise[].justification`. This makes the judge's reasoning auditable and prevents bare-number comparisons.

---

## INDEX.md row

When a round closes, append one row to `runs/INDEX.md`. The column order is fixed:

| Column | Source |
|---|---|
| Round | `manifest.json → round` |
| Date | `manifest.json → date` |
| Case | `manifest.json → case` @ `manifest.json → case_version` |
| Hypothesis | `manifest.json → hypothesis` |
| Arms | Comma-separated `manifest.json → arm` values across repetitions |
| N per arm | Count of repetitions per arm |
| Outcome | One-line summary: winning arm and margin, or "inconclusive" |
| Delta cleared spread? | "yes" / "no" / "inconclusive" per the decision rule in `scoring.md` |

Write the row only after all repetitions of the round are scored and the round report is complete. A partial round does not appear in the index.

---

## Threats to validity

Every report's `## Threats to validity` section must address the following seed list. Add run-specific items beyond the seed list; never shorten it. "None" is never an acceptable answer — if a threat does not apply to a specific run, explain why it does not apply; do not omit the row.

| Threat | What to address |
|---|---|
| **Public probes are not secret** | Solvers trained on public data may have seen probe inputs. State whether a private overlay was used (see `## Private probe overlay`). If probes were public-only, say so explicitly. |
| **N=1 noise** | A single repetition per arm cannot separate signal from run-to-run variance. State N and whether additional repetitions are planned. A round at N=1 is preliminary; do not draw conclusions from it. |
| **Judge bias** | The judge model may favour style or structure that resembles its own training distribution. Confirm that `judge.json → judge_family` is disjoint from `families_under_test`. Record any position flips in `judge.json → position_flips`. |
| **Spec ambiguity** | Ambiguous requirements may have been scored under one reading that favours one arm. If identified, state the ambiguity and score both readings. Fix the ambiguity in the next case version. |
| **Provider conditions** | Rate limits, latency spikes, or outages during a run affect `wall_clock_seconds` and `attempts`. Record any incidents from `manifest.environment.provider_incidents`. |
| **Frozen-base staleness** | The scaffold is pinned to `manifest.base_commit_sha`. If the upstream project has changed since freeze, the case may test a stale surface. State the freeze date and whether the upstream has diverged. |

---

## Private probe overlay

**Threat:** public probes in `probes/` may have appeared in solver training data, making probe scores unreliable as a signal of generalisation.

**Mitigation:** for any round whose result will be published or used to justify spend, replace `probes/` with a private overlay:

- Same interface as `probes/` (same command contract, same pass/fail output format).
- Same `SHA256SUMS` discipline — the overlay ships with a `SHA256SUMS` file; the evaluator verifies it before running.
- Held **outside this repository** to prevent accidental disclosure.
- The overlay's root directory hash is recorded in `manifest.json` under `environment` so the round is auditable without the probes being disclosed.

A round run on public probes only **must say so explicitly** in its `## Threats to validity` section. It may not be presented as a final result without this disclosure.

---

## Publishing

Before sharing a result outside the team:

1. Confirm the round has **more than one repetition per arm**, or label the result explicitly as **exploratory**.
2. Confirm `## Threats to validity` is present and not answered "none".
3. Confirm the private probe overlay was used, or disclose that it was not.
4. Confirm `runs/INDEX.md` has been updated with the round row.

A result that does not meet all four conditions may be shared internally for discussion but must be labelled preliminary and must not be used to justify spend or configuration decisions.
