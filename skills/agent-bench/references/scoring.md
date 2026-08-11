# Scoring reference

> **Scope.** This document defines every formula used to turn evaluator output into numbers. Stage 4 (`evaluator-4-judge.md`) applies the `L` formula defined here. Nothing outside this file may redefine these formulas; changes are a version bump of this document.

---

## Common core

Every run produces these metrics regardless of family. Source fields refer to `telemetry.json` and `verdict.json`.

| Metric | Source field | Notes |
|---|---|---|
| `cost_usd` | `telemetry.totals.cost_usd` | Basis recorded in `cost_basis` |
| `wall_clock_seconds` | `telemetry.totals.wall_clock_seconds` | Raw wall-clock including stalls |
| `wall_clock_seconds_net` | `telemetry.totals.wall_clock_seconds_net_of_rate_limits` | Comparable across provider conditions |
| `input_tokens` | `telemetry.totals.input_tokens` | |
| `output_tokens` | `telemetry.totals.output_tokens` | |
| `cache_read_tokens` | `telemetry.totals.cache_read_tokens` | |
| `cache_write_tokens` | `telemetry.totals.cache_write_tokens` | |
| `agent_invocations` | `telemetry.totals.agent_invocations` | |
| `attempts` | `telemetry.totals.attempts` | Retries by the solver |
| `convergence` | `telemetry.convergence` | `converged`, `aborted_on_budget`, or `required_human_intervention` |
| `gates_passed` | `verdict.gates_passed` | Boolean; gate details in `verdict.gates` |
| `probes_passed` | `verdict.probes.passed` | Count of probes that passed |
| `probes_total` | `verdict.probes.total` | |
| `acceptance_passed` | `verdict.acceptance.passed_items` | |
| `acceptance_total` | `verdict.acceptance.total_items` | |
| `confirmed_bugs` | `findings.confirmed_count` | Only findings with `reproduced: true` (see `evaluator-3-bughunt.md`) |
| `files_touched` | `telemetry.process_hygiene.files_touched` | |

Cost by role is reported from `telemetry.by_role[].cost_usd` aggregated per `role` value.

---

## Composite

The composite score for a single run is:

```
Q = 0.8 x correctness_normalized + 0.2 x efficiency
efficiency = 0.5 x min(1, best_cost/cost) + 0.5 x min(1, best_time/time)
Composite = 0.6 x Q + 0.4 x L
```

**`best_cost`** is the lowest `cost_usd` among the arms of this comparison.
**`best_time`** is the lowest `wall_clock_seconds_net_of_rate_limits` among the arms of this comparison.
**`L`** is the weighted-median judge score divided by 5 (`judge.json` field `L`; weights are defined in `evaluator-4-judge.md` and must not be redefined here).

`best_cost` and `best_time` are determined at round close using all arms of **this comparison only**. They are not global records. Composites computed under different baselines cannot be compared. See `## Never` below.

`efficiency` is bounded `[0, 1]` by the `min(1, ...)` caps: a run cannot score above 1 even if it is cheaper or faster than the baseline (baseline is always the best observed arm, not an external target).

---

## correctness_normalized by family

> **First-round defaults.** All four formulas below are initial estimates. They will be revised after round 1 shows which terms actually move across arms. Do not treat them as permanent until a revision record exists.

### L / S (long and short greenfield)

```
correctness_normalized =
  (acceptance_share x 30 + gates_passed x 10 + probe_share x 10
   + max(0, 10 - 2 x confirmed_bugs)) / 60
```

Term traceability:

| Term | Source | Computation |
|---|---|---|
| `acceptance_share` | `verdict.acceptance` | `passed_items / total_items`; range `[0, 1]` |
| `gates_passed` | `verdict.gates_passed` | Boolean cast to `{0, 1}` |
| `probe_share` | `verdict.probes` | `passed / total`; range `[0, 1]` |
| `confirmed_bugs` | `findings.confirmed_count` | Findings where `reproduced: true` only (see `evaluator-3-bughunt.md`) |

Denominator is 60 (maximum achievable raw score when all terms are maximised and `confirmed_bugs = 0`). The bug penalty bottoms out at 0 (five or more confirmed bugs).

### **B** (bug hunt on a seeded codebase)

> **First-round default — to be revised after round 1.**

```
correctness_normalized =
  0.5 x recall
  + 0.3 x precision
  + 0.2 x (1 - false_positive_rate_on_control)
```

Term definitions:

| Term | Definition | Source |
|---|---|---|
| `recall` | seeded defects found / seeded defects present | `findings.json`; only findings with `seeded_defect_id` set and `reproduced: true` count as found |
| `precision` | reproduced findings / total findings | `findings.confirmed_count / (confirmed_count + unreproduced_count)` |
| `false_positive_rate_on_control` | findings raised on the zero-defect control arm / total findings on control | Requires a control arm with no seeded defects; rate of `reproduced: true` findings on that arm |

`false_positive_rate_on_control` requires running a zero-defect control arm in the same round. If no control arm is present, this term is treated as 0.

### **R** (multi-file refactor)

> **First-round default — to be revised after round 1.**

```
correctness_normalized =
  0.6 x site_coverage
  + 0.3 x regression_free
  + 0.1 x (1 - scope_creep_ratio)
```

Term definitions:

| Term | Definition | Source |
|---|---|---|
| `site_coverage` | files in the sealed site list that were touched / total files in the sealed site list | `verdict.family_outcome.site_coverage`; site list comes from the case spec |
| `regression_free` | 1 if the full base suite plus probes all pass; 0 otherwise | All-or-nothing; `verdict.gates_passed` and `verdict.probes.passed == verdict.probes.total` |
| `scope_creep_ratio` | files touched outside the sealed site list / total files touched | `telemetry.process_hygiene.files_touched`; files in site list vs out-of-site files tracked in `verdict.family_outcome.scope_creep_ratio` |

### **M** (multi-session continuity)

> **First-round default — to be revised after round 1.**

```
correctness_normalized =
  0.4 x final_outcome
  + 0.3 x rediscovery_efficiency
  + 0.2 x continuity
  + 0.1 x (1 - rework_ratio)
```

Term definitions:

| Term | Definition | Source |
|---|---|---|
| `final_outcome` | L / S formula applied to the last leg | Computed from `verdict.json` of the final leg |
| `rediscovery_efficiency` | `min(1, best_rediscovery_cost_usd / rediscovery_cost_usd)` — the arm with the lowest rediscovery cost scores 1.0; others score proportionally less | `verdict.family_outcome.rediscovery_efficiency`; `best_rediscovery_cost_usd` is the minimum across all arms in this comparison (same relative-to-best normalisation as `efficiency`) |
| `continuity` | share of the sealed leg-1 decision checklist still honoured at the end of the run | `verdict.family_outcome.continuity`; checklist is sealed and hashed at the end of leg 1 |
| `rework_ratio` | lines rewritten of already-delivered work / total lines delivered | `verdict.family_outcome.rework_ratio`; rewritten means lines present in a prior leg's diff that are removed or replaced in a later leg |

**Reweighting rationale (v1 → v2):** the original formula weighted `final_outcome` at 0.5 and omitted rediscovery. Review of `M-relay` showed that a no-memory arm can recover all four leg-1 design decisions by reading the repository (≈100 lines), so `continuity` and `rework_ratio` do not reliably discriminate. The only quantity that genuinely differs between arms is what it costs to rediscover. `rediscovery_efficiency` is therefore the primary discriminating term, weighted at 0.3 — enough that a 2× difference in recall cost produces a 0.15 difference in `correctness_normalized`, which resolves through `Q` as roughly 0.07 in `Composite`. `final_outcome` remains the largest term (0.4) because a solver that converges on the correct contract still scores higher than one that does not. `continuity` drops to 0.2 and `rework_ratio` to 0.1 because both are recoverable signals that will be nearly identical across arms when rediscovery is available.

**`rediscovery_cost_usd` definition:** tokens consumed before the first file write or code-edit tool call at the start of each continuation leg (legs 2 and 3), converted to USD using the same rate as `telemetry.totals.cost_usd`. The evaluator sums this across both continuation legs. If the harness does not record per-leg telemetry, set `rediscovery_cost_usd` to the per-leg average derived from `telemetry.by_role` and document the estimation method. If per-leg breakdowns are entirely unavailable, set `rediscovery_efficiency` to `null` and exclude it from `correctness_normalized` (reduce the denominator accordingly and document the exclusion).

---

## Aborted runs

An aborted run (`telemetry.convergence == "aborted_on_budget"` or `"required_human_intervention"`) is a result, not a void. Consistent with `run-protocol.md`:

- Score the partial outcome using the applicable family formula.
- Cap `Composite` at **0.50** regardless of the partial score.
- The cap applies after computing the full formula; do not skip any formula step.
- Record `convergence` prominently in the per-run report.

---

## Decision rule

Report ranges, not bare medians. At N per arm:

- Compute the median and the full observed range (min–max) for every signal.
- An arm wins a signal only when the **delta between arm medians exceeds the within-arm spread of the wider arm**.
- Never declare an arm the winner overall unless a majority of signals meet this delta criterion.
- At N=3, treat any signal whose ranges overlap as inconclusive.

**Concrete precedent.** In `orquesta-lite/benchmark/context-metrics/`, at N=3 only three of six measured signals had non-overlapping ranges. Three of six is not a win; it is a mixed result. A round at N=3 is exploratory unless confirmed by additional repetitions.

---

## Never

- **No cross-case aggregate.** Do not sum or average composites from different cases. Cases differ in difficulty, scope, and family; the number means nothing across them.
- **No leaderboard.** Do not rank arms across rounds in a single table. Each round's `best_cost` and `best_time` baselines differ; composites computed under different baselines are not comparable by construction.
- **No cross-baseline comparison.** Do not compare a Composite from one round with a Composite from a different round unless `best_cost` and `best_time` are identical in both rounds. This constraint is not advisory — the efficiency term is defined relative to the best observed arm in this comparison, so a composite computed in a different comparison is on a different scale.
