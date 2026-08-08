# Run protocol

Read this before phases 2 and 3. Cross-reference the matching `references/solvers/*.md` note for the exact solver invocation.

## Isolation

- Create one fresh clone or `git worktree` per run per repetition.
- Never reuse another run's state directory, partial checkouts, or leftovers from a prior arm.
- Never resume a run across arms. Each arm starts from a clean base at `manifest.base_commit_sha`.

## Building the working copy

The solver's working copy is assembled by copying only `scaffold/` and `spec/` from the case directory. Evaluation material is never placed within the solver's reach.

| Copy into working copy | Never copy |
|---|---|
| `scaffold/` | `probes/` |
| `spec/` | `acceptance.md` |
| | `rubric.md` |

Verify before launch (run in the solver's working copy root):

```sh
test ! -e probes && test ! -e acceptance.md && test ! -e rubric.md && echo "clean"
```

Proceed only when this command prints `clean`.

## Pre-flight checklist

Walk each item before every launch. These items come from operational failures recorded in a prior benchmark round.

- [ ] Binary under test is pinned and its version recorded in the manifest; no mid-round rebuilds.
- [ ] Timeouts and attempt budgets are set at launch, not raised mid-run.
- [ ] The policy or budget file in effect is recorded, and its path is outside any directory whose contents are validated against a manifest.
- [ ] Both gates are green at scaffold HEAD.
- [ ] The tree is a fresh clone with no residue from a previous run.
- [ ] Sleep is inhibited for the whole run (`caffeinate -i` on macOS); a machine that sleeps corrupts wall-clock.
- [ ] `manifest.json` is written and committed before launch.

## Launch

Launch headless and detached. Redirect all output to a log path and record that path in `telemetry.source_logs`.

Flag ordering matters for some CLIs. Copy the exact invocation from the matching solver note:

| Solver | Note |
|---|---|
| orq-lite | `references/solvers/orq-lite.md` |
| claude-code | `references/solvers/claude-code.md` |
| opencode | `references/solvers/opencode.md` |
| codex | `references/solvers/codex.md` |

Before launch verify these manifest fields are complete:

| Field | Check |
|---|---|
| `manifest.solver.launch_command` | Matches the actual command character-for-character |
| `manifest.solver.binaries` | Each entry has `name`, `version`, and `sha256` |
| `manifest.base_commit_sha` | SHA of the scaffold HEAD given to the solver |
| `manifest.environment.sleep_inhibited` | Set to `true` |

## During the run

Zero manual intervention once the solver is running.

If a provider incident occurs, record it in `manifest.environment.provider_incidents` with `start` and `end` timestamps in ISO 8601. Do not restart, skip ahead, or patch outputs during the incident.

## Aborts

An abort is a result, not a failure to be repaired.

| Condition | Required action |
|---|---|
| Budget hit (`max_usd` or `max_wall_clock_seconds` reached) | Record `convergence: aborted_on_budget` in `telemetry.json` |
| Partial solver output exists | Score the partial outcome as-is |
| Composite score | Cap at 0.50 for any aborted run |

Do **not** patch by hand and resume. Do **not** raise the budget ceiling and rerun.

## After the run

Archive in this order:

1. The work branch — push or tag it; never delete it.
2. The raw solver log — already recorded in `telemetry.source_logs`.
3. Gate output at HEAD from a **fresh checkout** — re-run gates on a clean tree, not the solver's working copy.
