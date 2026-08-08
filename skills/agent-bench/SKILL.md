---
name: agent-bench
description: Use when comparing coding-agent configurations — different models, flags, MCP servers, subagent strategies, or orchestration runtimes — to design the experiment, run it under isolation, evaluate the result blind, and record the evidence. Covers benchmark design, token/cost/time telemetry, hidden-probe verdicts, adversarial bug hunts, and LLM-as-a-judge scoring.
---

# agent-bench

This skill orchestrates rigorous comparisons between coding-agent **configurations**, not models in the abstract; the goal is to attribute a measured outcome to a specific change. A comparison is only meaningful when exactly one independent variable differs between arms — everything else is held constant and hashed.

## The three pieces

| Piece | Contract |
|---|---|
| **Case** | Owns the task spec the solver sees, the pristine scaffold, and the evaluation material the solver must never see (hidden probes, acceptance list, judge rubric); versioned as `<ID>@<n>`. |
| **Solver** | Any command that takes the pristine scaffold plus the prompt and produces a git branch; no adapter interface — `manifest.json` records the exact launch command, binary versions, config hashes, base SHA, and prompt, all written before launch. |
| **Evaluator** | Runs blind against a fresh clone of the solver's branch; four independent subagent stages each emit a typed JSON output contract; no solver self-report enters the verdict. |

## Protocol

| Phase | Action | Gate |
|---|---|---|
| 1. Frame | State hypothesis, the single independent variable, the held-constant set, case and family, N, budget, stop rule | Stop and re-frame if more than one variable differs between arms. Stop if the case's "What this case does NOT measure" section covers the hypothesis |
| 2. Prepare | Pristine scaffold per run in an isolated worktree, frozen binaries, pre-flight checklist, `manifest.json` written before launch | Both gates green at scaffold HEAD, and `probes/` absent from the solver's working copy |
| 3. Run | Headless launch, zero manual intervention, incidents recorded | An abort is a result; never patch by hand and resume |
| 4. Evaluate | Four evaluator stages as independent subagents against a fresh clone | No solver self-report enters the verdict |
| 5. Report | Scorecard, `INDEX.md` row, threats to validity | No winner declared inside the spread |

## Read before acting

| Phase / Topic | Reference |
|---|---|
| 1. Frame | `references/experiment-design.md` |
| 2. Prepare | `references/run-protocol.md` + matching solver note below |
| 3. Run | `references/run-protocol.md` + matching solver note below |
| 4. Evaluate — stage 1 telemetry | `references/evaluator-1-telemetry.md` (backed by `references/telemetry.md`) |
| 4. Evaluate — stage 2 verdict | `references/evaluator-2-verdict.md` |
| 4. Evaluate — stage 3 bug hunt | `references/evaluator-3-bughunt.md` |
| 4. Evaluate — stage 4 judge | `references/evaluator-4-judge.md` |
| 5. Report | `references/scoring.md`, `references/reporting.md` |
| Case authoring | `references/adding-a-case.md` |

Solver notes — read the one that matches the solver under test:

| Solver | Note |
|---|---|
| orq-lite | `references/solvers/orq-lite.md` |
| claude-code | `references/solvers/claude-code.md` |
| opencode | `references/solvers/opencode.md` |
| codex | `references/solvers/codex.md` |

## Hard rules

- Exactly one independent variable per comparison; everything else is asserted byte-identical and hashed in the manifest.
- The evaluator runs the gates and the probes itself; the solver's self-report never enters the verdict.
- A bug-hunt finding without a reproduction does not count.
- The judge model must not belong to any family under test, and may not contradict the deterministic results.
- Report ranges with N, never bare medians.
- An arm wins only when the delta exceeds the within-arm spread; otherwise report a tie.
- An aborted run is a data point, not a failure to be repaired.

## Ledger

Destination resolves in order:

1. `$AGENT_BENCH_HOME` if set.
2. The current repository, if it is an agent-bench checkout.
3. `./bench-runs/` with a warning that results are not being recorded to the catalog.

Each run directory contains:

| File | Purpose |
|---|---|
| `manifest.json` | Launch record written before the solver starts |
| `telemetry.json` | Token, cost, and wall-time measurements |
| `verdict.json` | Hidden-probe pass/fail results |
| `findings.json` | Bug-hunt findings with reproductions |
| `judge.json` | LLM-as-a-judge scores and rationale |
| `report.md` | Human-readable scorecard |
| `diff.patch` | Solver output as a diff against the base SHA |

Generated code is never committed to the ledger — only `diff.patch` against the base SHA.

## Adding a case

See `references/adding-a-case.md` for the full authoring workflow, directory layout, and required fields.
