# agent-bench — design

Date: 2026-08-07

A benchmark repository for comparing coding-agent configurations. It ships one
skill that drives the whole protocol and a catalog of cases the skill runs
against. It contains no maintained executable harness of its own.

## 1. Problem

Comparisons between agent configurations are currently run ad hoc. Each round
reinvents its launch procedure, its telemetry extraction, and its scoring, and
the resulting numbers are not comparable across rounds. The prior work in
`orquesta-lite/benchmark/` proves the methodology is sound — deterministic
verdicts, blind probes, adversarial bug hunts, out-of-family judges — but it is
welded to one runtime (`orq-lite`), one project shape (greenfield FastAPI
build), and one round's operational decisions.

The goal is a generic, reusable structure that answers questions of the form
"does configuration A beat configuration B on this kind of work, and at what
cost", for configurations as different as:

- `orq-lite` governed flow with `fast=true` vs `fast=false`
- an agent with a memory MCP server vs the same agent without it
- superpowers with subagents on Sonnet vs on GPT
- `orq-lite` as solver vs `opencode` + an orquesta skill as solver

## 2. Non-goals

- **Not a leaderboard.** Scores are comparable between arms within one case.
  They are not comparable across cases, and no cross-case aggregate is produced.
- **Not a maintained CLI.** No `agentbench run` command, no Python package, no
  CI. The skill is prose; the cases are data.
- **Not a general SWE-bench replacement.** The catalog is small, hand-written,
  and tuned to the failure modes worth separating in this work.

## 3. Architecture

Three pieces, each with an explicit contract.

### 3.1 Case

A case is the task under which solvers are compared. It owns the spec the solver
sees, the pristine starting state, and — critically — the evaluation material
the solver must never see.

```
skills/agent-bench/cases/<ID>/
├── case.md          # family, version, expected duration/cost, what it measures,
│                    # and an explicit "what this case does NOT measure" section
├── spec/            # what the solver receives: features.md + CONVENTIONS.md
├── scaffold/        # exact initial tree + bootstrap commands; both gates green at HEAD
├── probes/          # frozen hidden tests + SHA256 manifest + application instructions
├── acceptance.md    # mechanical checklist, one item per observable criterion
└── rubric.md        # case-specific anchors for the quality judge
```

Cases are versioned as `<ID>@<n>`. Editing `spec/`, `probes/`, or
`acceptance.md` bumps the version; existing runs stay bound to the version they
scored against.

The "what this case does NOT measure" section in `case.md` is a hard
requirement, not documentation garnish. It is what stops a greenfield build case
from being used to draw conclusions about persistent memory.

### 3.2 Solver

The configuration under test. Deliberately unconstrained: any command that takes
the pristine scaffold plus the prompt and leaves a git branch qualifies.

There is no solver registry and no adapter interface. The only requirement is
that `manifest.json` records, before launch:

- the exact launch command, verbatim
- versions of every binary involved (agent CLI, runtime, provider CLIs)
- a hash of every config file that differs from the other arms, plus the list of
  files asserted identical
- the base commit SHA
- the prompt, verbatim
- environment notes: machine, whether sleep was inhibited, provider conditions

`references/solvers/*.md` holds optional field notes per tool (headless
invocation, where the log lands, which stream format it emits). These are a
convenience, not a contract — they may go stale and the protocol does not depend
on them.

### 3.3 Evaluator

Runs against a fresh clone of the resulting branch, blind to which solver
produced it. Four stages, each an independent subagent with a JSON output
contract. The separation is the point: a mistake in stage 2 must not contaminate
stage 4.

| Stage | Input | Output | LLM |
|---|---|---|---|
| 1. Telemetry | solver log | `telemetry.json` | No |
| 2. Verdict | fresh clone + `probes/` + `acceptance.md` | `verdict.json` | Only to walk the checklist; every item backed by a command |
| 3. Bug hunt | `git diff <base>...HEAD` | `findings.json` | Yes, prompted to refute; every finding needs a reproduction |
| 4. Judge | blinded tree + `rubric.md` + stages 1-3 | `judge.json` | Yes, out-of-family, position-swapped, 3 samples |

Rules carried over from `orquesta-lite/benchmark/evaluation.md`:

- The evaluator runs the gates itself. The solver's self-report never enters the
  verdict.
- A bug-hunt finding without a reproduction does not count.
- The judge receives the deterministic results and may not contradict them.
- Every judge score cites `file:line` or command output; unevidenced scores are
  discarded and resampled.
- Judge model must not belong to any family under test.

## 4. Repository layout

```
agent-bench/                              # npx skills add collectiveai-team/agent-bench
├── README.md
├── skills/agent-bench/
│   ├── SKILL.md
│   ├── references/
│   │   ├── experiment-design.md
│   │   ├── run-protocol.md
│   │   ├── telemetry.md
│   │   ├── evaluator-1-telemetry.md
│   │   ├── evaluator-2-verdict.md
│   │   ├── evaluator-3-bughunt.md
│   │   ├── evaluator-4-judge.md
│   │   ├── scoring.md
│   │   ├── reporting.md
│   │   ├── adding-a-case.md
│   │   └── solvers/{orq-lite,claude-code,opencode,codex}.md
│   ├── templates/
│   │   ├── manifest.json
│   │   ├── telemetry.json
│   │   ├── verdict.json
│   │   ├── findings.json
│   │   ├── judge.json
│   │   └── report.md
│   └── cases/
│       ├── CATALOG.md
│       └── <case dirs>
└── runs/
    ├── INDEX.md
    └── <YYYY-MM-DD>-<case>-<solver>-r<n>/
```

The repository is `git@github.com:collectiveai-team/agent-bench.git`.
Distribution is `npx skills add collectiveai-team/agent-bench` (the
`vercel-labs/skills` CLI), which copies `skills/agent-bench/` into
`~/.agents/skills/` and symlinks it into each harness. This drives one layout constraint: **everything the skill
needs at runtime lives inside its own folder**, cases included. Cases are text
and small trees, so this is cheap.

`runs/` sits outside the skill folder because it is committed evidence, not
shipped material. The skill resolves the ledger destination in order:

1. `$AGENT_BENCH_HOME`
2. the current repo, if it is an agent-bench checkout
3. `./bench-runs/`, with a warning that results are not being recorded to the
   catalog

## 5. Case catalog

All cases share one stack (`uv` + pytest + ruff) so gates are byte-identical
across families and a solver adapter written once works everywhere.

| ID | Family | Base | Expected | What it separates |
|---|---|---|---|---|
| `L-taskflow` | Long greenfield | ported from `orquesta-lite/benchmark/features.md` | 2-6 h, $15-60 | End-to-end capability, governance, convergence |
| `L-hookrelay` | Long greenfield | ported from `orquesta-lite/benchmark/round2/` | 2-6 h, $15-60 | A second spec, so conclusions do not rest on one |
| `S-ledger` | Short greenfield | new | 15-45 min, $1-4 | Idempotency keys, boundary math on balances, error bodies. Cheap enough for N>=5 |
| `S-ingest` | Short greenfield | new | 15-45 min, $1-4 | Schema-validating ingest CLI with bad-row quarantine. Non-API, so "short" is not always the same shape |
| `B-sabotage` | Bug hunt | frozen good `L-taskflow` implementation + defect patches | 10-30 min, $1-3 | Detection rather than authoring; bug-hunter roles |
| `R-envelope` | Multi-file refactor | same frozen base | 30-90 min, $2-8 | Complete sweep over a sealed site list; where subagents vs single session should separate |
| `M-relay` | Multi-session | `S-ledger` split into 3 legs with cold context between | 1-2 h, $4-12 | Continuity; the only design where a memory MCP can produce signal |

Three decisions inside this:

**`B-sabotage` reuses already-built repositories.** Its base is a frozen good
implementation taken from a prior round's output. Each defect is a versioned
patch that leaves both gates green while violating an observable criterion — the
pattern already validated in `orquesta-lite/benchmark/context-metrics/`. The
case includes a **zero-defect control arm**; without it, false-positive rate
cannot be measured, and a hunter that invents findings looks excellent.

**`R-envelope` shares that frozen base**, so a realistic repository costs
nothing extra to obtain.

**`M-relay` is built on a short case, not a long one.** Measuring continuity
requires context cuts, not task size; running it on `L-taskflow` would cost
roughly 10x for the same signal.

## 6. Metrics

### 6.1 Common core — identical for every family

Derived from the solver's own log; no LLM involved.

- Tokens `in / out / cache_read / cache_write`, per invocation and total
- Cost in USD, and cost per outcome point
- Wall-clock, total and net of rate-limit stalls
- Agent invocations, turns, attempts/retries per unit of work
- Convergence: finished unaided / aborted on budget / required human
  intervention
- Process hygiene: commits, diff size, files touched

### 6.2 Outcome — defined per family

| Family | Outcome | Quality judge |
|---|---|---|
| L / S | acceptance % · gates (all-or-nothing) · hidden-probe % · confirmed post-hoc bugs (penalty) | On the code |
| B | recall over seeded defects · precision (reproduced findings / total) · false positives on the control arm · cost per defect found | On the **report**, not the code |
| R | coverage over the sealed site list · regressions (base suite + probes) · scope creep (files touched out of scope) · gates | On the code |
| M | continuity (leg-1 decisions still honored at leg 3, sealed checklist) · rework (lines rewritten of already-delivered work) · rediscovery (tokens spent re-reading the same material) · final case outcome | On the code |

### 6.3 Composite and decision rule

The composite is computed **within a case**, never across cases. Every family
shares one shape, inherited from `orquesta-lite/benchmark/evaluation.md`:

```
Q = 0.8 x correctness_normalized + 0.2 x efficiency
efficiency = 0.5 x min(1, best_cost/cost) + 0.5 x min(1, best_time/time)
Composite = 0.6 x Q + 0.4 x L        # L = weighted median judge score / 5
```

Only `correctness_normalized` differs per family. First-round defaults, to be
revised once round 1 shows which terms actually move:

| Family | `correctness_normalized` |
|---|---|
| L / S | verbatim from `evaluation.md` §2.1: acceptance 30 · gates 10 · probe 10 · bugs (10 − 2/confirmed, floor 0), out of 60 |
| B | `0.5 x recall + 0.3 x precision + 0.2 x (1 − false_positive_rate_on_control)` |
| R | `0.6 x site_coverage + 0.3 x regression_free (all-or-nothing) + 0.1 x (1 − scope_creep_ratio)` |
| M | `0.5 x final_outcome (S-ledger acceptance+probe) + 0.3 x continuity + 0.2 x (1 − rework_ratio)` |

Rediscovery cost in family M is reported, not scored — it is already captured by
the common-core token metrics and scoring it twice would double-count.

Results are reported as **ranges with N**, not medians. An arm wins only when
the delta exceeds the within-arm spread; otherwise the result is a tie and is
reported as a tie. This is the explicit lesson of
`orquesta-lite/benchmark/context-metrics/README.md`, where at n=3 only three of
six measured signals had non-overlapping ranges.

## 7. Run ledger

```
runs/2026-08-07-taskflow-orqlite-fast-r1/
├── manifest.json     # case@version, solver command + versions + config hashes,
│                     # base SHA, prompt, environment
├── telemetry.json
├── verdict.json
├── findings.json
├── judge.json
├── report.md
└── diff.patch        # generated code is not committed; only the diff vs base SHA
```

`runs/INDEX.md` aggregates by round: hypothesis, arms, N, outcome, and whether
the delta cleared the spread.

## 8. Skill protocol

`SKILL.md` drives five phases, each with a gate.

| Phase | Action | Gate |
|---|---|---|
| 1. Frame | State the hypothesis, the single independent variable, the held-constant set, the case and family, N, budget, and stop rule | Stop and re-frame if more than one variable differs between arms. Stop if the case's "does NOT measure" section covers the hypothesis |
| 2. Prepare | Pristine scaffold per run in an isolated worktree, frozen binaries, pre-flight checklist, `manifest.json` written **before** launch | Both gates green at scaffold HEAD |
| 3. Run | Headless launch, zero manual intervention, incidents recorded | An abort is a result, not something to patch by hand and resume |
| 4. Evaluate | The four evaluator stages as independent subagents against a fresh clone | No solver self-report enters the verdict |
| 5. Report | Scorecard, `INDEX.md` entry, threats to validity | No winner declared inside the spread |

A secondary flow, `adding-a-case.md`, covers authoring: every acceptance
criterion must be observable by a command, and probes must be written **before**
any implementation is seen.

The pre-flight checklist in phase 2 is seeded from the operational failures
already recorded in `orquesta-lite/benchmark/round4/README.md`: timeouts raised
mid-run, policies reset by hand after aborts, stale pinned binaries, and a Mac
falling asleep and corrupting wall-clock.

## 9. Threats to validity

Carried into `reporting.md` as a required section of every report.

- **Hidden probes in a public repository are not secret.** They are hidden from
  the solver at runtime but are indexable and trainable. Acceptable for
  comparing arms today; the skill must state this, and high-stakes rounds should
  use a private probe overlay.
- **N=1 noise.** Agentic runs are high-variance. The short cases exist
  specifically so N>=5 is affordable.
- **Judge bias.** Mitigated by out-of-family judge, blinding, position swap, and
  the evidence requirement; residual bias is why the composite stays
  majority-deterministic.
- **Spec ambiguity.** A criterion two arms read differently is scored for both
  readings, flagged, and fixed in the next case version rather than penalizing
  an arm.
- **Provider conditions.** Rate limits distort both wall-clock and retry counts.
  Incident windows are recorded in the manifest.
- **Frozen-base staleness.** `B-sabotage` and `R-envelope` depend on a frozen
  implementation. When it is regenerated, both cases bump version, and prior
  runs are not comparable to later ones.

## 10. Migration from existing material

| Source | Destination |
|---|---|
| `benchmark/features.md`, `CONVENTIONS.md`, `probe/` | `cases/L-taskflow/` |
| `benchmark/round2/{features,CONVENTIONS}.md`, `round2/probe/` | `cases/L-hookrelay/` |
| `benchmark/evaluation.md` sections 2-4 | `references/scoring.md` (L/S family), `evaluator-*.md` |
| `benchmark/evaluation.md` section 5 | `references/reporting.md` |
| `benchmark/round4/README.md` pre-flight checklist | `references/run-protocol.md` |
| `context-metrics/reference/extract.py` stream-format knowledge | `references/telemetry.md`, as prose per format |
| `context-metrics/README.md` range-overlap discipline | `references/scoring.md` decision rule |
| `taskflow-r4-*` output repos | frozen base for `B-sabotage` / `R-envelope` |

`orquesta-lite/benchmark/` is left in place; agent-bench copies from it rather
than moving it, so the `cutover-evidence.json` gate in that repo keeps working.
