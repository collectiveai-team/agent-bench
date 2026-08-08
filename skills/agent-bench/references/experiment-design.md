# Experiment design

Read this before phase 1. Gate: stop and re-frame if more than one variable differs between arms. Stop if the case's `## What this case does NOT measure` section covers the hypothesis.

## The hypothesis form

Every comparison must begin with a written hypothesis in this exact form:

> Configuration A beats configuration B on \<family\> work, at \<cost relation\>.

Write it down before any run. A hypothesis that cannot be stated in this form indicates the comparison is not ready.

Examples:
- "orq-lite fast=true beats fast=false on refactor work, at equal or lower cost."
- "Memory MCP enabled beats disabled on stateful-context work, within 1.5× cost."

## One variable

Exactly one independent variable may differ between arms. Everything else must be asserted byte-identical and hashed in the manifest.

| Comparison | Independent variable | Must be held constant |
|---|---|---|
| `orq-lite` governed `fast=true` vs `fast=false` | one flag | flow, pack, policy, team.json, prompts, binary build, case version, machine |
| memory MCP on vs off | presence of one MCP server | agent binary, model, prompt, tool permissions, case version |
| superpowers subagents on Sonnet vs on GPT | subagent model assignment | skill version, subagent count and roles, orchestrator model, prompt |
| `orq-lite` vs `opencode` + orquesta skill | **the whole solver stack** | case, spec, gates, N, machine. This one measures the stack, not a single knob — the report must say so explicitly |

When the fourth comparison type is used, the report must state plainly that it is a stack comparison, not a controlled experiment over a single variable, and that no causal attribution to any one component is valid from its result.

## Held-constant set

Before any run:

1. List every held-constant element in `manifest.held_constant` (array of strings).
2. Hash every config file relevant to the solver in `manifest.solver.config_files`, one entry per file:
   - `path` — repo-relative path to the file
   - `sha256` — SHA-256 of the file at launch time
   - `differs_between_arms` — `true` only if this file is the independent variable; `false` if it must be byte-identical across arms
3. Confirm that no `config_files` entry has `differs_between_arms: true` unless it corresponds to the single independent variable.

## Choosing N

N is chosen from the case's expected cost and the available budget **before** seeing any results. Never set or revise N after observing outcomes.

| Case length | N rule |
|---|---|
| Short (expected cost ≤ $1) | N ≥ 5 |
| Long (expected cost > $1) | N ≥ 3 if affordable; N = 1 explicitly labelled exploratory-only |

An exploratory-only run (N = 1) must be marked as such in the report and may not be used to declare a winner.

## Budget and stop rule

Fill `manifest.budget` completely before launch:

| Field | Requirement |
|---|---|
| `max_usd` | Dollar ceiling for the entire run |
| `max_wall_clock_seconds` | Wall-clock ceiling for the entire run |
| `stop_rule` | One of: `first_arm_exhausted`, `all_arms_exhausted`, or a quoted natural-language rule |

If the budget is exhausted during a run:
- Record `convergence: aborted_on_budget` in `telemetry.json`.
- Score the partial outcome as-is and cap the composite at 0.50.
- Do **not** retry with a raised ceiling mid-round. Raising the limit mid-round invalidates the budget as a controlled variable.

## When the case cannot answer the hypothesis

Before launch, read the **`## What this case does NOT measure`** section in `case.md`.

If that section covers or directly excludes the hypothesis, abandon the pairing and choose a different case. Do not proceed with a known-invalid pairing.

| Example mismatch | Correct action |
|---|---|
| Memory-MCP hypothesis tested on a single-session greenfield case | Use `M-relay` instead; single-session cases cannot exercise memory carry-over |
