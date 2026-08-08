# agent-bench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `collectiveai-team/agent-bench` — a benchmark repository containing one installable skill that drives a five-phase comparison protocol, and a catalog of seven cases across five families, with no maintained executable harness.

**Architecture:** Three contracts — a **case** (spec + pristine scaffold + frozen hidden probes + mechanical acceptance list), a **solver** (any command producing a branch, recorded verbatim in a manifest), and an **evaluator** (four blind stages with JSON outputs). The skill is prose under `skills/agent-bench/`; cases are data inside that folder so they travel with `npx skills add`; run evidence is committed to `runs/` outside it.

**Tech Stack:** Markdown and JSON only. Cases target Python 3.12 + `uv` + pytest + ruff so gate commands are byte-identical across every case.

## Global Constraints

- **Everything in the repository is written in English.** Prose, filenames, commit messages, JSON keys.
- **No executable harness is created.** No Python package, no CLI entry point, no CI workflow, no `pyproject.toml` at the repo root. Scripts appear only as copy-pasteable commands inside reference documents.
  **Carve-out — case data is not harness.** A case legitimately ships `.py` files: `probes/test_probe.py`, `defects/*/detect.py`, and a scaffold's own `pyproject.toml`. These are the case's frozen evaluation material, versioned with the case and executed only against a solver's output. They are never imported by the skill, never shared between cases except where a task says so explicitly, and never grow into a runner. Reviewers must not flag them as harness.
- **Repository:** `git@github.com:collectiveai-team/agent-bench.git`, branch `main`, already initialized locally at `/Users/lionelchamorro/Projects/collectiveai/agent-bench` with two commits and `origin` configured.
- **Skill install path must stay `skills/agent-bench/SKILL.md`** — this is what the `vercel-labs/skills` CLI resolves. Anything the skill needs at runtime lives under `skills/agent-bench/`.
- **Case gate commands, verbatim, in every case:** `uv run ruff check .` and `uv run pytest -q`.
- **Case version syntax:** `<ID>@<n>`, e.g. `L-taskflow@1`. Editing `spec/`, `probes/`, or `acceptance.md` bumps `n`.
- **Source of truth for ported material:** `/Users/lionelchamorro/Projects/personal/orquesta-lite/benchmark/`. Copy from it; never move or delete anything there, because `cutover-evidence.json` in that repository still references it.
- **Every markdown document ends with a trailing newline and uses ATX headings (`#`).**
- **Commit after every task**, message in Conventional Commits form, English, with the trailing line:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`

---

## File Structure

### Repository root (outside the skill — not shipped by `npx skills add`)

| File | Responsibility |
|---|---|
| `README.md` | What the repo is, how to install the skill, how to run a comparison, link to the spec |
| `.gitignore` | Python/venv/cache noise plus `bench-runs/` |
| `runs/INDEX.md` | One row per round: date, hypothesis, arms, N, outcome, whether the delta cleared the spread |
| `docs/superpowers/specs/2026-08-07-agent-bench-design.md` | Already committed. The approved design |
| `docs/superpowers/plans/2026-08-07-agent-bench.md` | This plan |

### Skill (shipped by `npx skills add`)

| File | Responsibility |
|---|---|
| `skills/agent-bench/SKILL.md` | Entry point. Frontmatter + the five-phase protocol + a routing table to references. Nothing else — detail lives in references |
| `references/experiment-design.md` | Phase 1. Hypothesis form, single-variable rule, held-constant set, choosing N, budget, stop rule |
| `references/run-protocol.md` | Phases 2-3. Isolation, pre-flight checklist, launch hygiene, incident recording, abort handling |
| `references/telemetry.md` | Evaluator stage 1 data source. Exact JSON paths per provider stream format |
| `references/evaluator-1-telemetry.md` | Stage 1 subagent brief + output contract |
| `references/evaluator-2-verdict.md` | Stage 2 subagent brief + output contract |
| `references/evaluator-3-bughunt.md` | Stage 3 subagent brief + output contract |
| `references/evaluator-4-judge.md` | Stage 4 subagent brief + output contract + bias controls |
| `references/scoring.md` | Common core metrics, per-family correctness normalization, composite, decision rule |
| `references/reporting.md` | Scorecard assembly, `INDEX.md` row format, mandatory threats-to-validity section |
| `references/adding-a-case.md` | Authoring flow for a new case, including probe-before-implementation rule |
| `references/solvers/orq-lite.md` | Field notes: headless launch, log location, stream format |
| `references/solvers/claude-code.md` | Same, for Claude Code |
| `references/solvers/opencode.md` | Same, for opencode |
| `references/solvers/codex.md` | Same, for codex |
| `templates/manifest.json` | Ledger template, all keys present with empty/null values |
| `templates/telemetry.json` | Stage 1 output shape |
| `templates/verdict.json` | Stage 2 output shape |
| `templates/findings.json` | Stage 3 output shape |
| `templates/judge.json` | Stage 4 output shape |
| `templates/report.md` | Scorecard skeleton |
| `cases/CATALOG.md` | The seven cases, their families, expected cost/duration, and what each does not measure |
| `cases/_base-taskflow/` | Frozen good Taskflow implementation shared by `B-sabotage` and `R-envelope` |
| `cases/L-taskflow/` | Long greenfield, ported |
| `cases/L-hookrelay/` | Long greenfield, ported |
| `cases/S-ledger/` | Short greenfield, API shape |
| `cases/S-ingest/` | Short greenfield, CLI shape |
| `cases/B-sabotage/` | Bug hunt over `_base-taskflow` |
| `cases/R-envelope/` | Multi-file refactor over `_base-taskflow` |
| `cases/M-relay/` | Multi-session, three legs over `S-ledger` |

### Case internal layout (identical for every case)

```
cases/<ID>/
├── case.md          # family, version, expected duration/cost, what it measures,
│                    # and a "What this case does NOT measure" section
├── spec/            # what the solver receives
├── scaffold/        # pristine starting tree + bootstrap commands
├── probes/          # hidden tests + SHA256SUMS + VALIDATION.md
├── acceptance.md    # mechanical checklist, one item per observable criterion
└── rubric.md        # case-specific judge anchors
```

`B-sabotage` replaces `scaffold/` with `defects/` (patch files) and `R-envelope` adds `sites.md` (the sealed site list); both are documented in their tasks.

**Deviation from the approved spec:** the spec's §3.1 case layout does not mention a shared frozen base. Task 14 adds `cases/_base-taskflow/` and amends §3.1 and §5 of the spec in the same commit, so the spec stays the source of truth.

---

## Phase A — Skill core (Tasks 1-9)

### Task 1: Repository skeleton

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `runs/INDEX.md`

- [ ] **Step 1: Write `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/
.DS_Store
bench-runs/
```

- [ ] **Step 2: Write `README.md`**

Required content, in this order:

1. Title `# agent-bench` and a one-paragraph statement: a benchmark repository for comparing coding-agent configurations; one skill drives the protocol, a catalog of cases supplies the work, and no executable harness is maintained.
2. `## Install` section with exactly:

```sh
npx skills add collectiveai-team/agent-bench
```

   followed by one sentence stating this copies `skills/agent-bench/` into `~/.agents/skills/` and symlinks it into each harness's skills directory.
3. `## Use` section: invoke the `agent-bench` skill and state the comparison. One worked one-liner example: *"Compare orq-lite `factory_governed` with `fast=true` against `fast=false` on `S-ledger`, N=5."*
4. `## What is in here` table with three rows — `skills/agent-bench/` (the protocol and the case catalog), `runs/` (committed evidence, one directory per run), `docs/superpowers/` (design spec and implementation plan).
5. `## Ledger location` section listing the resolution order verbatim: `$AGENT_BENCH_HOME`, then the current repository if it is an agent-bench checkout, then `./bench-runs/` with a warning that results are not being recorded to the catalog.
6. `## Design` section linking `docs/superpowers/specs/2026-08-07-agent-bench-design.md`.

- [ ] **Step 3: Write `runs/INDEX.md`**

```markdown
# Run index

One row per round. A round is one hypothesis tested across two or more arms.

| Round | Date | Case | Hypothesis | Arms | N per arm | Outcome | Delta cleared spread? |
|---|---|---|---|---|---|---|---|
```

- [ ] **Step 4: Verify the tree**

Run: `git status --short && ls -R runs`
Expected: three untracked paths (`README.md`, `.gitignore`, `runs/`); `runs` contains only `INDEX.md`.

- [ ] **Step 5: Verify no harness leaked in**

Run: `ls pyproject.toml setup.py .github 2>&1`
Expected: `No such file or directory` for all three.

- [ ] **Step 6: Commit**

```bash
git add README.md .gitignore runs/INDEX.md
git commit -m "feat: repository skeleton and run ledger index

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Ledger templates

**Files:**
- Create: `skills/agent-bench/templates/manifest.json`
- Create: `skills/agent-bench/templates/telemetry.json`
- Create: `skills/agent-bench/templates/verdict.json`
- Create: `skills/agent-bench/templates/findings.json`
- Create: `skills/agent-bench/templates/judge.json`
- Create: `skills/agent-bench/templates/report.md`

**Interfaces:**
- Produces: the exact key names every later reference document and evaluator stage writes. Tasks 5, 6, 7 and 9 must use these names and no others.

- [ ] **Step 1: Write `templates/manifest.json`**

```json
{
  "run_id": "",
  "date": "",
  "round": "",
  "case": "",
  "case_version": "",
  "family": "",
  "arm": "",
  "repetition": 0,
  "hypothesis": "",
  "independent_variable": "",
  "held_constant": [],
  "solver": {
    "launch_command": "",
    "prompt_verbatim": "",
    "binaries": [{ "name": "", "version": "", "sha256": "" }],
    "config_files": [{ "path": "", "sha256": "", "differs_between_arms": false }],
    "mcp_servers": [],
    "model_assignments": {}
  },
  "base_commit_sha": "",
  "work_branch": "",
  "environment": {
    "machine": "",
    "os_version": "",
    "sleep_inhibited": false,
    "launched_at": "",
    "provider_incidents": []
  },
  "budget": { "max_usd": 0, "max_wall_clock_seconds": 0, "stop_rule": "" }
}
```

- [ ] **Step 2: Write `templates/telemetry.json`**

```json
{
  "run_id": "",
  "source_logs": [],
  "totals": {
    "input_tokens": 0,
    "output_tokens": 0,
    "reasoning_tokens": 0,
    "cache_read_tokens": 0,
    "cache_write_tokens": 0,
    "cost_usd": 0.0,
    "wall_clock_seconds": 0,
    "wall_clock_seconds_net_of_rate_limits": 0,
    "agent_invocations": 0,
    "turns": 0,
    "attempts": 0,
    "rate_limit_events": 0
  },
  "by_role": [
    {
      "role": "",
      "provider": "",
      "model": "",
      "invocations": 0,
      "input_tokens": 0,
      "output_tokens": 0,
      "cache_read_tokens": 0,
      "cache_write_tokens": 0,
      "cost_usd": 0.0,
      "duration_seconds": 0
    }
  ],
  "convergence": "converged | aborted_on_budget | required_human_intervention",
  "process_hygiene": { "commits": 0, "diff_lines_added": 0, "diff_lines_removed": 0, "files_touched": 0 },
  "cost_basis": "reported_by_provider | computed_from_token_counts",
  "cost_basis_note": ""
}
```

- [ ] **Step 3: Write `templates/verdict.json`**

```json
{
  "run_id": "",
  "evaluated_commit_sha": "",
  "fresh_clone_path": "",
  "gates": {
    "ruff": { "command": "uv run ruff check .", "exit_code": null, "passed": false },
    "pytest": { "command": "uv run pytest -q", "exit_code": null, "passed": false, "tests_collected": 0 }
  },
  "gates_passed": false,
  "probes": {
    "sha256_verified": false,
    "command": "",
    "passed": 0,
    "total": 0,
    "failures": []
  },
  "acceptance": {
    "total_items": 0,
    "passed_items": 0,
    "items": [{ "id": "", "criterion": "", "verification_command": "", "observed": "", "passed": false }]
  },
  "family_outcome": {}
}
```

- [ ] **Step 4: Write `templates/findings.json`**

```json
{
  "run_id": "",
  "diff_range": "",
  "hunt_list_used": [],
  "findings": [
    {
      "id": "",
      "title": "",
      "location": "",
      "claim": "",
      "reproduction": { "kind": "test | curl | websocket_transcript | command", "content": "", "observed_output": "" },
      "reproduced": false,
      "seeded_defect_id": null,
      "severity": "blocking | note"
    }
  ],
  "confirmed_count": 0,
  "unreproduced_count": 0
}
```

- [ ] **Step 5: Write `templates/judge.json`**

```json
{
  "run_id": "",
  "judge_model": "",
  "judge_family": "",
  "families_under_test": [],
  "blinded_as": "",
  "samples": 3,
  "absolute": [
    {
      "sample": 1,
      "dimensions": [
        { "dimension": "", "score": 0, "evidence": ["file:line — reason"], "worst_finding": "" }
      ]
    }
  ],
  "pairwise": [
    { "sample": 1, "position": "A,B", "dimension": "", "winner": "A | B | tie", "justification": "" }
  ],
  "median_scores": {},
  "L": 0.0,
  "position_flips": [],
  "discarded_unevidenced_scores": 0
}
```

- [ ] **Step 6: Write `templates/report.md`**

```markdown
# <round> — <case>@<version> — <arm> r<n>

**Hypothesis:** <one sentence>
**Independent variable:** <the single thing that differs>
**Held constant:** <list, with the assertion of byte-identity>

## Delivery

| | |
|---|---|
| Convergence | |
| Attempts / retries | |
| Commits | |

## Correctness

| Metric | Value |
|---|---|
| Acceptance | / (%) |
| Gates | pass / fail |
| Hidden probes | / (%) |
| Confirmed bugs | |

## Efficiency

| Metric | Value |
|---|---|
| Cost (USD) | |
| Cost basis | reported / computed |
| Tokens in / out / cache read / cache write | |
| Wall-clock (total / net of stalls) | |
| Cost per outcome point | |

## Judge

| Dimension | Median score | Worst finding |
|---|---|---|

## Score

| | |
|---|---|
| correctness_normalized | |
| efficiency | |
| Q | |
| L | |
| **Composite** | |

## Threats to validity

<Required. Never omitted, never "none".>
```

- [ ] **Step 7: Verify every JSON template parses**

Run: `for f in skills/agent-bench/templates/*.json; do python3 -m json.tool "$f" > /dev/null && echo "OK $f"; done`
Expected: five `OK` lines, exit 0.

- [ ] **Step 8: Commit**

```bash
git add skills/agent-bench/templates
git commit -m "feat: ledger templates for manifest, telemetry, verdict, findings, judge

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: SKILL.md

**Files:**
- Create: `skills/agent-bench/SKILL.md`

**Interfaces:**
- Consumes: template key names from Task 2.
- Produces: the reference filenames every later task must create, exactly as routed here.

- [ ] **Step 1: Write the frontmatter**

```markdown
---
name: agent-bench
description: Use when comparing coding-agent configurations — different models, flags, MCP servers, subagent strategies, or orchestration runtimes — to design the experiment, run it under isolation, evaluate the result blind, and record the evidence. Covers benchmark design, token/cost/time telemetry, hidden-probe verdicts, adversarial bug hunts, and LLM-as-a-judge scoring.
---
```

- [ ] **Step 2: Write the body**

Required structure, in this order, and nothing more — detail belongs in references:

1. `# agent-bench` and a two-sentence framing: this skill compares configurations, not models in the abstract; a comparison is only meaningful when exactly one variable differs.
2. `## The three pieces` — a table with rows **Case**, **Solver**, **Evaluator** and their one-line contracts, matching spec §3.
3. `## Protocol` — the five phases as a table with columns Phase / Action / Gate, using these exact phase names and gate texts:

| Phase | Action | Gate |
|---|---|---|
| 1. Frame | State hypothesis, the single independent variable, the held-constant set, case and family, N, budget, stop rule | Stop and re-frame if more than one variable differs between arms. Stop if the case's "What this case does NOT measure" section covers the hypothesis |
| 2. Prepare | Pristine scaffold per run in an isolated worktree, frozen binaries, pre-flight checklist, `manifest.json` written before launch | Both gates green at scaffold HEAD, and `probes/` absent from the solver's working copy |
| 3. Run | Headless launch, zero manual intervention, incidents recorded | An abort is a result; never patch by hand and resume |
| 4. Evaluate | Four evaluator stages as independent subagents against a fresh clone | No solver self-report enters the verdict |
| 5. Report | Scorecard, `INDEX.md` row, threats to validity | No winner declared inside the spread |

4. `## Read before acting` — routing table mapping each phase to its reference file, listing all ten references plus the four solver notes by exact path — fourteen files in total, exactly the set the File Structure section above enumerates.
5. `## Hard rules` — a bulleted list of exactly these seven, each one line:
   - Exactly one independent variable per comparison; everything else is asserted byte-identical and hashed in the manifest.
   - The evaluator runs the gates and the probes itself; the solver's self-report never enters the verdict.
   - A bug-hunt finding without a reproduction does not count.
   - The judge model must not belong to any family under test, and may not contradict the deterministic results.
   - Report ranges with N, never bare medians.
   - An arm wins only when the delta exceeds the within-arm spread; otherwise report a tie.
   - An aborted run is a data point, not a failure to be repaired.
6. `## Ledger` — the destination resolution order and the run directory file list from spec §7.
7. `## Adding a case` — one sentence pointing at `references/adding-a-case.md`.

- [ ] **Step 3: Verify the frontmatter and required anchors**

Run:
```sh
head -1 skills/agent-bench/SKILL.md
grep -c '^name: agent-bench$' skills/agent-bench/SKILL.md
for a in '## The three pieces' '## Protocol' '## Read before acting' '## Hard rules' '## Ledger' '## Adding a case'; do
  grep -qF "$a" skills/agent-bench/SKILL.md && echo "OK $a" || echo "MISSING $a"
done
```
Expected: first line `---`, count `1`, six `OK` lines.

- [ ] **Step 4: Verify SKILL.md stayed an index, not a manual**

Run: `wc -l < skills/agent-bench/SKILL.md`
Expected: fewer than 150. If larger, move detail into a reference file.

- [ ] **Step 5: Commit**

```bash
git add skills/agent-bench/SKILL.md
git commit -m "feat: agent-bench skill entry point with five-phase protocol

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Experiment design and run protocol references

**Files:**
- Create: `skills/agent-bench/references/experiment-design.md`
- Create: `skills/agent-bench/references/run-protocol.md`

- [ ] **Step 1: Write `experiment-design.md`**

Required sections and content:

1. `## The hypothesis form` — mandate the shape *"Configuration A beats configuration B on <family> work, at <cost relation>"*, and require it be written down before any run.
2. `## One variable` — the rule, plus a worked table of the four motivating comparisons showing what is the variable and what must be held constant in each:

| Comparison | Independent variable | Must be held constant |
|---|---|---|
| `orq-lite` governed `fast=true` vs `fast=false` | one flag | flow, pack, policy, team.json, prompts, binary build, case version, machine |
| memory MCP on vs off | presence of one MCP server | agent binary, model, prompt, tool permissions, case version |
| superpowers subagents on Sonnet vs on GPT | subagent model assignment | skill version, subagent count and roles, orchestrator model, prompt |
| `orq-lite` vs `opencode` + orquesta skill | the whole solver | case, spec, gates, N, machine. This one measures the stack, not a single knob — say so in the report |
3. `## Held-constant set` — require enumerating it in `manifest.held_constant`, hashing every config file in `manifest.solver.config_files`, and marking which differ.
4. `## Choosing N` — state the rule: N is chosen from the case's expected cost and the budget, never after seeing results. Give the guidance table: short cases N>=5, long cases N>=3 if affordable and N=1 explicitly labelled exploratory-only.
5. `## Budget and stop rule` — require `manifest.budget` filled before launch, and that exhausting it is recorded as `aborted_on_budget`, not retried with a raised limit mid-round.
6. `## When the case cannot answer the hypothesis` — instruct reading the case's "What this case does NOT measure" section and abandoning the pairing if it matches. Give the canonical example: a memory-MCP hypothesis cannot be tested on a single-session greenfield case; use `M-relay`.

- [ ] **Step 2: Write `run-protocol.md`**

Required sections:

1. `## Isolation` — one fresh clone or `git worktree` per run per repetition; never reuse another run's state directory; never resume across arms.
2. `## Building the working copy` — the working copy is assembled by copying only `scaffold/` and `spec/` from the case. State explicitly that `probes/`, `acceptance.md`, and `rubric.md` are never copied, and give the verification command:

```sh
test ! -e probes && test ! -e acceptance.md && test ! -e rubric.md && echo "clean"
```

3. `## Pre-flight checklist` — a checkbox list seeded from the operational failures recorded in `orquesta-lite/benchmark/round4/README.md`, with these items verbatim:
   - Binary under test is pinned and its version recorded in the manifest; no mid-round rebuilds.
   - Timeouts and attempt budgets are set at launch, not raised mid-run.
   - The policy or budget file in effect is recorded, and its path is outside any directory whose contents are validated against a manifest.
   - Both gates are green at scaffold HEAD.
   - The tree is a fresh clone with no residue from a previous run.
   - Sleep is inhibited for the whole run (`caffeinate -i` on macOS); a machine that sleeps corrupts wall-clock.
   - `manifest.json` is written and committed before launch.
4. `## Launch` — headless, detached, output redirected to a log path recorded in `telemetry.source_logs`. Note that flag ordering matters for some CLIs and to copy the exact invocation from the matching `references/solvers/*.md`.
5. `## During the run` — zero manual intervention. Record provider incidents with start and end timestamps in `manifest.environment.provider_incidents`.
6. `## Aborts` — an abort is a result. Record `convergence: aborted_on_budget`, score the partial outcome, and cap the composite at 0.50. Do not patch by hand and resume.
7. `## After the run` — archive the work branch, the raw solver log, and the gate output at HEAD from a fresh checkout.

- [ ] **Step 3: Verify required anchors**

Run:
```sh
for a in '## The hypothesis form' '## One variable' '## Held-constant set' '## Choosing N' '## Budget and stop rule' '## When the case cannot answer the hypothesis'; do
  grep -qF "$a" skills/agent-bench/references/experiment-design.md || echo "MISSING $a"
done
for a in '## Isolation' '## Building the working copy' '## Pre-flight checklist' '## Launch' '## During the run' '## Aborts' '## After the run'; do
  grep -qF "$a" skills/agent-bench/references/run-protocol.md || echo "MISSING $a"
done
grep -qF 'caffeinate -i' skills/agent-bench/references/run-protocol.md || echo "MISSING caffeinate"
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add skills/agent-bench/references/experiment-design.md skills/agent-bench/references/run-protocol.md
git commit -m "feat: experiment design and run protocol references

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Telemetry reference

**Files:**
- Create: `skills/agent-bench/references/telemetry.md`

**Interfaces:**
- Consumes: `templates/telemetry.json` key names from Task 2.
- Produces: the per-format extraction rules that `evaluator-1-telemetry.md` (Task 6) cites.

Source of truth for this document is `orquesta-lite/benchmark/context-metrics/reference/extract.py`. Transcribe its knowledge as prose and `jq` recipes; do not copy the script into this repository.

- [ ] **Step 1: Write the format sections**

`## Claude Code stream (`--output-format stream-json`)`

One JSON object per line. Relevant records:

| Record | Path | Maps to |
|---|---|---|
| `type == "system"`, `subtype == "init"` | `.cwd`, `.tools`, `.mcp_servers`, `.permissionMode` | run context; `len(.mcp_servers)` is how a memory-MCP arm is verified as actually active |
| `type == "assistant"` | `.message.content[] \| select(.type=="tool_use")` | tool counts, files read/written, subagent dispatches |
| `type == "result"` | `.usage.input_tokens`, `.usage.output_tokens`, `.usage.cache_read_input_tokens`, `.usage.cache_creation_input_tokens`, `.total_cost_usd`, `.num_turns`, `.duration_ms`, `.is_error`, `.stop_reason` | totals |
| `type == "rate_limit_event"` | count of lines | `rate_limit_events` |

Include this recipe:

```sh
jq -s 'map(select(.type=="result")) | .[0] |
  {input: .usage.input_tokens, output: .usage.output_tokens,
   cache_read: .usage.cache_read_input_tokens,
   cache_write: .usage.cache_creation_input_tokens,
   cost_usd: .total_cost_usd, turns: .num_turns, duration_ms: .duration_ms}' stdout.log
```

`## Codex stream`

| Record | Path | Maps to |
|---|---|---|
| `type == "turn.completed"` | `.usage.input_tokens`, `.usage.cached_input_tokens`, `.usage.output_tokens`, `.usage.reasoning_output_tokens` | totals |
| `type == "item.completed"`, `.item.type == "command_execution"` | `.item.command` | bash activity; strip the `/bin/zsh -lc "` wrapper before classifying |
| `type == "item.completed"`, `.item.type == "file_change"` | `.item.changes[].path` | files written |
| `type == "item.completed"`, `.item.type == "agent_message"` | count | turns |

State the three corrections that must be applied, because they are not obvious from the field names:
- `input_tokens` is **inclusive of** `cached_input_tokens`. Report `input = input_tokens - cached_input_tokens` and `cache_read = cached_input_tokens`, or the arm double-counts cached input.
- `reasoning_output_tokens` must be **added into** `output_tokens`, and also reported separately in `reasoning_tokens`.
- Codex emits no cost field. Set `cost_basis: "computed_from_token_counts"` and record the rate used in `cost_basis_note`.

`## opencode stream`

| Record | Path | Maps to |
|---|---|---|
| `type == "step_finish"` | `.part.tokens.input`, `.part.tokens.output`, `.part.tokens.reasoning`, `.part.tokens.cache.read`, `.part.tokens.cache.write`, `.part.cost` | **accumulate across every step**, unlike Claude and Codex which report a single total |
| `type` in `tool`/`part_updated` with `.part.type == "tool"` | `.part.tool`, `.part.state.input`, `.part.state.status` | tool activity; only count `status == "completed"`, and de-duplicate on `(tool, input)` because parts are re-emitted on update |

`## orq-lite runs`

Per-invocation artifacts live under `.orquestalite/runs/<run_id>/agents/<activity>/<invocation>/`, with `meta.json` (`provider`, `agent`, `model`, `session_id`, `duration_s`, `exit_code`), `prompt.md`, and `stdout.log`. The invocation directory name encodes role, cycle, attempt and retry as `<role>.c<N>.a<N>[.r<N>]` — parse it to fill `telemetry.by_role` and the `attempts` total. The provider field selects which of the three parsers above applies to `stdout.log`.

- [ ] **Step 2: Write the cross-cutting sections**

1. `## Wall-clock net of rate limits` — total wall-clock minus the summed duration of provider-incident windows recorded in the manifest and the `rate_limit_event` spans in the log.
2. `## Cost basis` — providers that report cost set `reported_by_provider`; providers that do not require computing from token counts at a rate written into `cost_basis_note`. Never mix the two bases within one comparison without saying so in the report: this is exactly what made the round-4 gpt-sol cost figure incomparable until it was recomputed.
3. `## Verifying the arm is what you think it is` — for MCP arms, assert `n_mcp_servers` differs between arms and matches intent; for model arms, assert `meta.json.model` in every invocation matches the assignment; for fallback-capable runtimes, check whether the artifact was actually produced by the intended agent and label the run if it was not.

- [ ] **Step 3: Verify required anchors**

Run:
```sh
for a in 'cache_read_input_tokens' 'cache_creation_input_tokens' 'cached_input_tokens' 'reasoning_output_tokens' 'step_finish' '.part.tokens.cache.read' 'cost_basis' '## Verifying the arm is what you think it is'; do
  grep -qF "$a" skills/agent-bench/references/telemetry.md || echo "MISSING $a"
done
```
Expected: no output.

- [ ] **Step 4: Verify no script was vendored**

Run: `ls skills/agent-bench/references/*.py 2>&1`
Expected: `No such file or directory`.

- [ ] **Step 5: Commit**

```bash
git add skills/agent-bench/references/telemetry.md
git commit -m "feat: multi-provider telemetry extraction reference

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: The four evaluator stage briefs

**Files:**
- Create: `skills/agent-bench/references/evaluator-1-telemetry.md`
- Create: `skills/agent-bench/references/evaluator-2-verdict.md`
- Create: `skills/agent-bench/references/evaluator-3-bughunt.md`
- Create: `skills/agent-bench/references/evaluator-4-judge.md`

**Interfaces:**
- Consumes: template shapes from Task 2, extraction rules from Task 5.
- Produces: four subagent briefs. Each file must contain a `## Subagent brief` section written in the second person, ready to be pasted as a subagent prompt verbatim.

Every one of the four files has the same skeleton: `## Purpose`, `## Inputs`, `## Procedure`, `## Output contract`, `## Refusals`. `## Refusals` lists what this stage must never do.

- [ ] **Step 1: Write `evaluator-1-telemetry.md`**

- Purpose: fill `telemetry.json`. No LLM judgement, no code reading.
- Inputs: the solver's raw logs, `manifest.json`.
- Procedure: identify the format, apply `references/telemetry.md`, aggregate totals and per-role rows, compute wall-clock net of incidents, set `convergence` and `cost_basis`, compute process hygiene from `git diff --shortstat <base>...HEAD` and `git rev-list --count <base>..HEAD`.
- Refusals: never read the source tree to form an opinion; never take a cost figure from the agent's own prose.

- [ ] **Step 2: Write `evaluator-2-verdict.md`**

- Purpose: fill `verdict.json`.
- Inputs: a fresh clone of the work branch at the evaluated SHA, the case's `probes/` and `acceptance.md`.
- Procedure, in order:
  1. Clone fresh into a new directory; never evaluate in the solver's working copy.
  2. Verify probe integrity: `shasum -a 256 -c probes/SHA256SUMS` must pass before probes are copied in. A mismatch aborts the evaluation.
  3. Run both gates, record exit codes verbatim. Gates are all-or-nothing.
  4. Copy probes into the clone, run them, record pass/total and every failure's node id.
  5. Walk `acceptance.md` item by item. Each item is scored only by executing its `verification_command` and recording the observed output. **Reading the source and concluding the criterion is met is not permitted** — the round-4 evaluators produced false positives exactly this way.
  6. Fill `family_outcome` using the family's section of `references/scoring.md`.
- Refusals: never accept the solver's test suite as evidence of the criterion; never mark an item passed without an observed command output; never repair the branch to make a gate pass.

- [ ] **Step 3: Write `evaluator-3-bughunt.md`**

- Purpose: fill `findings.json`.
- Inputs: `git diff <base_commit_sha>...HEAD`, the spec, the case rubric.
- Procedure: read the diff prompted to **refute** the implementation's quality. Work the hunt list, then look beyond it. Every claim requires a reproduction — a test, a curl transcript, a websocket transcript, or a command with its observed output. Claims that do not reproduce are recorded with `reproduced: false` and do not count.
- The hunt list, verbatim, drawn from this project's field lessons:
  - partial-update data loss (a PATCH that overwrites unset fields)
  - write paths that bypass validation
  - earlier features broken by later ones
  - boundary and rounding math
  - joins on name instead of id
  - N+1 queries
  - leaked tasks or subscriptions
  - events published inside a transaction
  - naive/aware datetime loss across a persistence round-trip
  - assertions or invariant checks placed outside the error handling that is supposed to contain them
  - module-level state that should be scoped to the application instance
  - check-then-act races on uniqueness constraints
- Refusals: never count an unreproduced claim; never report style preferences as defects; never fix what you find.

- [ ] **Step 4: Write `evaluator-4-judge.md`**

- Purpose: fill `judge.json`.
- Inputs: the blinded tree, the case `rubric.md`, and the completed stages 1-3.
- Bias controls, all mandatory:
  - Judge model must not belong to any family under test. Record `judge_family` and `families_under_test` and assert disjointness.
  - Blind: export as `impl_A`/`impl_B` with random assignment; strip `.git/`, any runtime state directory, commit messages, and model-identifying strings.
  - Position swap: every pairwise question asked as (A,B) and (B,A); a verdict that flips is recorded in `position_flips` and scored as a tie.
  - Three independent samples; aggregate absolute scores by median and pairwise by majority.
  - Every score cites `file:line` or a command output; unevidenced scores are discarded, counted in `discarded_unevidenced_scores`, and resampled.
  - The judge receives stages 1-3 and may not contradict them.
- The seven default dimensions and weights, ported verbatim from `orquesta-lite/benchmark/evaluation.md` §3.2: spec fidelity 25%, correctness and robustness 20%, architecture and layering 15%, test quality 15%, concurrency and async correctness 10%, code quality and idiom 10%, docs and DX 5%. State that a case's `rubric.md` supplies the 1/3/5 anchors and may reweight, but the dimension set is fixed.
- For family **B**, state that the judge scores the **findings report**, not the code, on four dimensions instead: evidence quality 40%, severity calibration 25%, actionability 20%, absence of padding 15%.
- Refusals: never judge a dimension the rubric has no anchor for; never reward code volume, comments, or defensive boilerplate.

- [ ] **Step 5: Verify all four files carry the shared skeleton and a pasteable brief**

Run:
```sh
for f in 1-telemetry 2-verdict 3-bughunt 4-judge; do
  p="skills/agent-bench/references/evaluator-$f.md"
  for a in '## Purpose' '## Inputs' '## Procedure' '## Output contract' '## Refusals' '## Subagent brief'; do
    grep -qF "$a" "$p" || echo "MISSING $a in $p"
  done
done
grep -qF 'shasum -a 256 -c' skills/agent-bench/references/evaluator-2-verdict.md || echo "MISSING probe integrity check"
grep -qF 'position_flips' skills/agent-bench/references/evaluator-4-judge.md || echo "MISSING position swap"
```
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add skills/agent-bench/references/evaluator-*.md
git commit -m "feat: four blind evaluator stage briefs

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Scoring and reporting references

**Files:**
- Create: `skills/agent-bench/references/scoring.md`
- Create: `skills/agent-bench/references/reporting.md`

- [ ] **Step 1: Write `scoring.md`**

1. `## Common core` — the metric list from spec §6.1, each with its source field in `telemetry.json`.
2. `## Composite` — verbatim:

```
Q = 0.8 x correctness_normalized + 0.2 x efficiency
efficiency = 0.5 x min(1, best_cost/cost) + 0.5 x min(1, best_time/time)
Composite = 0.6 x Q + 0.4 x L
```

   with `best_cost` and `best_time` defined as the best value observed among the arms of **this comparison**, and `L` as the weighted median judge score divided by 5.
3. `## correctness_normalized by family` — four subsections, each stating the formula and how each term is obtained from `verdict.json`:
   - **L / S**: `(acceptance_share x 30 + gates_passed x 10 + probe_share x 10 + max(0, 10 - 2 x confirmed_bugs)) / 60`
   - **B**: `0.5 x recall + 0.3 x precision + 0.2 x (1 - false_positive_rate_on_control)`, where recall is seeded defects found over seeded defects present, precision is reproduced findings over total findings, and the false-positive rate comes from the zero-defect control arm.
   - **R**: `0.6 x site_coverage + 0.3 x regression_free + 0.1 x (1 - scope_creep_ratio)`, where `regression_free` is all-or-nothing over the base suite plus probes, and `scope_creep_ratio` is files touched outside the sealed site list over files touched.
   - **M**: `0.5 x final_outcome + 0.3 x continuity + 0.2 x (1 - rework_ratio)`, where `final_outcome` is the L/S formula applied to the last leg, continuity is the share of the sealed leg-1 decision checklist still honoured at the end, and `rework_ratio` is lines rewritten of already-delivered work over total lines delivered.
   Label these four as **first-round defaults, to be revised after round 1 shows which terms move**.
4. `## Not scored, only reported` — family M rediscovery cost, because the common-core token metrics already capture it and scoring it twice double-counts.
5. `## Aborted runs` — composite capped at 0.50, partial outcome still scored.
6. `## Decision rule` — report ranges with N, never bare medians. An arm wins only when the delta exceeds the within-arm spread. Cite the concrete precedent: in `orquesta-lite/benchmark/context-metrics/`, at n=3 only three of six measured signals had non-overlapping ranges.
7. `## Never` — no cross-case aggregate; no leaderboard; no comparison of composites computed under different `best_cost`/`best_time` baselines.

- [ ] **Step 2: Write `reporting.md`**

1. `## Per-run report` — fill `templates/report.md`; every number traceable to a ledger file.
2. `## Round report` — winner and margin, whether the margin exceeds the within-arm spread, the cost split by role, the confirmed-bug list, and the judge's justifications for the three largest gaps.
3. `## INDEX.md row` — the exact column order from `runs/INDEX.md`.
4. `## Threats to validity` — mandatory section in every report, never omitted and never "none". Seed list to review each time, from spec §9: public probes are not secret; N=1 noise; judge bias; spec ambiguity scored for both readings and fixed in the next case version; provider conditions; frozen-base staleness.
5. `## Private probe overlay` — the mitigation for the first threat. For a round whose result will be published or used to justify spend, replace `probes/` with an unpublished overlay: same interface, same `SHA256SUMS` discipline, held outside this repository, its hash recorded in the manifest so the round is auditable without the probe being disclosed. State that a round run on public probes only must say so in its report.
6. `## Publishing` — before sharing a result outside the team, confirm the round has more than one repetition per arm or is explicitly labelled exploratory.

- [ ] **Step 3: Verify required anchors**

Run:
```sh
grep -qF 'Composite = 0.6 x Q + 0.4 x L' skills/agent-bench/references/scoring.md || echo "MISSING composite"
for a in 'L / S' '**B**' '**R**' '**M**' '## Decision rule' '## Never'; do
  grep -qF "$a" skills/agent-bench/references/scoring.md || echo "MISSING $a"
done
grep -qF '## Threats to validity' skills/agent-bench/references/reporting.md || echo "MISSING threats"
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add skills/agent-bench/references/scoring.md skills/agent-bench/references/reporting.md
git commit -m "feat: scoring formulas per family and reporting rules

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Solver field notes

**Files:**
- Create: `skills/agent-bench/references/solvers/orq-lite.md`
- Create: `skills/agent-bench/references/solvers/claude-code.md`
- Create: `skills/agent-bench/references/solvers/opencode.md`
- Create: `skills/agent-bench/references/solvers/codex.md`

Each file opens with this exact disclaimer line, because these are conveniences and not contracts:

> These notes may go stale. The protocol depends only on `manifest.json` recording the exact command actually used.

Each file then carries: `## Headless launch`, `## Where the log lands`, `## Stream format`, `## Pinning the configuration`, `## Known traps`.

- [ ] **Step 1: Write `orq-lite.md`**

- Headless launch, with the flag-ordering trap called out — flags go immediately after the flow ref, before `key=value` arguments:

```sh
nohup caffeinate -i .orquestalite/bin/orq-lite flow run <pack>/<flow>@<v> \
  --policy=.orquestalite/<policy>.json \
  features_path=features.md \
  > /tmp/<run>-launch.log 2>&1 < /dev/null &
disown
```

- Log location: `.orquestalite/run.log` plus per-invocation artifacts under `.orquestalite/runs/<run_id>/agents/<activity>/<invocation>/`.
- Stream format: per-invocation, selected by `meta.json.provider`; see `references/telemetry.md`.
- Pinning: copy the built binary into the run directory and record its version and sha256; never rebuild mid-round.
- Known traps, each one line: `flow run` does not accept `--log-format`; a policy file placed inside a pack directory breaks pack validation with `pack: unlisted file`; without an explicit `--policy` an older pack silently falls back to the engine default budget; `orq-lite doctor` must be green before launch.

- [ ] **Step 2: Write `claude-code.md`**

- Headless launch with `--output-format stream-json` and the prompt supplied non-interactively, output redirected to a log recorded in `telemetry.source_logs`.
- Stream format: Claude section of `references/telemetry.md`.
- Pinning: record the CLI version, the model id, and the resolved settings; for MCP arms record the server list and assert `n_mcp_servers` differs as intended.
- Known traps: skills and plugins present in the environment change behaviour and must be part of the held-constant set or the independent variable; permission mode affects what the agent can do and must be identical across arms.

- [ ] **Step 3: Write `opencode.md`**

- Headless launch and log redirection.
- Stream format: opencode section of `references/telemetry.md`; totals accumulate across `step_finish` events.
- Pinning: `opencode models` to confirm the provider/model id actually resolves; a model id that does not resolve is a pre-launch blocker, not something to fix mid-run.
- Known traps: tool parts are re-emitted on update and must be de-duplicated; quota exhaustion pauses runs for long periods and distorts wall-clock.

- [ ] **Step 4: Write `codex.md`**

- Headless launch and log redirection.
- Stream format: Codex section of `references/telemetry.md`.
- Pinning: record CLI version and model id.
- Known traps: no cost field is emitted, so `cost_basis` is `computed_from_token_counts`; `input_tokens` includes cached input and must be corrected; reasoning tokens must be added into output.

- [ ] **Step 5: Verify the disclaimer and sections in all four**

Run:
```sh
for f in orq-lite claude-code opencode codex; do
  p="skills/agent-bench/references/solvers/$f.md"
  grep -qF 'These notes may go stale' "$p" || echo "MISSING disclaimer in $p"
  for a in '## Headless launch' '## Where the log lands' '## Stream format' '## Pinning the configuration' '## Known traps'; do
    grep -qF "$a" "$p" || echo "MISSING $a in $p"
  done
done
```
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add skills/agent-bench/references/solvers
git commit -m "feat: solver field notes for orq-lite, claude-code, opencode, codex

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Case authoring reference and catalog

**Files:**
- Create: `skills/agent-bench/references/adding-a-case.md`
- Create: `skills/agent-bench/cases/CATALOG.md`

**Interfaces:**
- Produces: the case layout contract and the `case.md` section list that Tasks 10-17 each satisfy.

- [ ] **Step 1: Write `adding-a-case.md`**

1. `## Layout` — the case directory tree from this plan's File Structure section.
2. `## case.md required sections` — exactly: `# <ID>`, `## Identity` (family, version, expected duration, expected cost), `## What it measures`, `## What this case does NOT measure`, `## Gates`, `## Provenance`.
3. `## Writing acceptance criteria` — every item must be observable by a command. Each item is a row with `id`, `criterion`, `verification_command`. Forbid criteria phrased as "the code should" and require "running X produces Y". Give one good and one bad example.
4. `## Writing probes` — probes are written **before any implementation is seen**. They are black-box: they exercise the contract through its public surface, never import internals. Freeze with:

```sh
cd probes && shasum -a 256 test_probe.py > SHA256SUMS
```

5. `## Validating probes without shipping a solution` — build a throwaway reference implementation outside the repository, run the probes against it, confirm all pass, then break one criterion deliberately and confirm the corresponding probe fails. Record both outputs in `probes/VALIDATION.md`. **The reference implementation is never committed** — a committed solution is a copyable answer key.
6. `## Probe defect log` — when a probe is found to be wrong, fix it, bump the case version, and append to `probes/VALIDATION.md` what was wrong and how it was detected, following the precedent of `orquesta-lite/benchmark/round2/probe/PROBE_DEFECTS.md`.
7. `## Scaffold` — must bootstrap to green gates with an empty or trivial suite, be committed and tagged, and contain no hint of the solution.

- [ ] **Step 2: Write `cases/CATALOG.md`**

A table with columns ID / Family / Base / Expected duration / Expected cost / What it separates / What it does not measure, one row per case, exactly matching spec §5 plus the "does not measure" column. Below it, a `## Choosing a case` section mapping hypothesis kinds to cases, including verbatim: *a memory or context-retention hypothesis requires `M-relay`; no single-session case can answer it.*

- [ ] **Step 3: Verify**

Run:
```sh
for a in '## Layout' '## case.md required sections' '## Writing acceptance criteria' '## Writing probes' '## Validating probes without shipping a solution' '## Probe defect log' '## Scaffold'; do
  grep -qF "$a" skills/agent-bench/references/adding-a-case.md || echo "MISSING $a"
done
grep -c '^| ' skills/agent-bench/cases/CATALOG.md
```
Expected: no `MISSING` lines; the count is at least 9 (header, separator, seven cases).

- [ ] **Step 4: Commit**

```bash
git add skills/agent-bench/references/adding-a-case.md skills/agent-bench/cases/CATALOG.md
git commit -m "feat: case authoring reference and catalog

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Phase B — Ported long cases (Tasks 10-11)

**Milestone:** at the end of Task 11 the repository is usable end to end. Every comparison the spec motivates can be run against `L-taskflow` or `L-hookrelay`. Phase C only widens the catalog.

### Task 10: Port L-taskflow

**Files:**
- Create: `skills/agent-bench/cases/L-taskflow/case.md`
- Create: `skills/agent-bench/cases/L-taskflow/spec/features.md` (copy)
- Create: `skills/agent-bench/cases/L-taskflow/spec/CONVENTIONS.md` (copy)
- Create: `skills/agent-bench/cases/L-taskflow/scaffold/BOOTSTRAP.md`
- Create: `skills/agent-bench/cases/L-taskflow/probes/test_probe.py` (copy)
- Create: `skills/agent-bench/cases/L-taskflow/probes/SHA256SUMS`
- Create: `skills/agent-bench/cases/L-taskflow/probes/VALIDATION.md`
- Create: `skills/agent-bench/cases/L-taskflow/acceptance.md`
- Create: `skills/agent-bench/cases/L-taskflow/rubric.md`

- [ ] **Step 1: Copy the ported material**

```bash
B=/Users/lionelchamorro/Projects/personal/orquesta-lite/benchmark
C=skills/agent-bench/cases/L-taskflow
mkdir -p $C/spec $C/scaffold $C/probes
cp $B/features.md      $C/spec/features.md
cp $B/CONVENTIONS.md   $C/spec/CONVENTIONS.md
cp $B/probe/test_probe.py $C/probes/test_probe.py
```

- [ ] **Step 2: Freeze the probe hash**

```bash
cd skills/agent-bench/cases/L-taskflow/probes && shasum -a 256 test_probe.py > SHA256SUMS && cd -
cat skills/agent-bench/cases/L-taskflow/probes/SHA256SUMS
```
Expected: one line, 64 hex characters followed by `  test_probe.py`.

- [ ] **Step 3: Write `scaffold/BOOTSTRAP.md`**

The exact bootstrap from `orquesta-lite/benchmark/README.md` §1, as a copy-pasteable block:

```sh
uv init --name taskflow --python 3.12
uv add fastapi uvicorn "sqlalchemy[asyncio]" aiosqlite "prefect>=3" pydantic-settings
uv add --dev pytest pytest-asyncio httpx ruff
mkdir -p app tests && touch app/__init__.py tests/__init__.py
```

plus the `pyproject.toml` additions:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 100
```

and the closing instruction: verify both gates are green, then `git add -A && git commit -m "chore: bench scaffold" && git tag bench-base`.

- [ ] **Step 4: Write `acceptance.md`**

Walk every bullet of `spec/features.md` — five `##` sections: application skeleton and SQLite persistence, jobs REST API, Prefect processing pipeline behind a dispatcher, WebSocket job event stream, stats endpoint and end-to-end verification. Produce one table row per observable criterion with columns `id`, `criterion`, `verification_command`.

Fix the granularity at **one item per observable criterion**, and state the count at the top of the file. This is a hard requirement: round 4 produced two evaluations of the same `features.md` at 27 and 59 items, which made the two acceptance percentages non-comparable. Record the frozen count in `case.md` under `## Identity`.

- [ ] **Step 5: Write `rubric.md`**

The seven dimensions from `evaluator-4-judge.md` with Taskflow-specific 1/3/5 anchors, ported from `orquesta-lite/benchmark/evaluation.md` §3.2 (the table there is already Taskflow-specific — copy its anchors verbatim).

- [ ] **Step 6: Write `case.md`**

Sections per `adding-a-case.md`. `## What this case does NOT measure` must state, at minimum: context retention across sessions, defect detection in existing code, and navigation of an unfamiliar codebase — this case starts from an empty tree.
`## Provenance` records the source path and that the material is copied, not moved.

Add one further section, `## Validity threat: a public reference implementation exists`, stating verbatim what it costs and why it was accepted:

> `cases/_base-taskflow/` in this same public repository is a complete, working implementation of this case's specification, kept because families B and R need a realistic codebase. It is a copyable answer key for `L-taskflow`. This does not distort a comparison — every arm has identical access to it — but it does expose the case to training-data contamination over time. Any round on this case whose result will be published or used to justify spend must run against a private probe overlay, per `references/reporting.md`.

This section is required. Task 12's rule that a reference implementation is never committed still holds for every other case; this is the single documented exception.

- [ ] **Step 7: Validate the probes against a known-good implementation**

`taskflow-r4-gpt-sol` is a Taskflow implementation that already scored 14/14 on this probe. Use it as the validation target.

**Its work was never committed.** Branch `bench-r4` there still points at the scaffold commit and the whole implementation is untracked in the working tree — so `git worktree add` or `git archive` would yield an empty `app/`. Copy the working tree instead:

```bash
SRC=/Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol
rm -rf /tmp/agb-probe-check
rsync -a --exclude '.git' --exclude '.orquestalite' --exclude '__pycache__' \
      --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude '.venv' \
      "$SRC/" /tmp/agb-probe-check/
cp skills/agent-bench/cases/L-taskflow/probes/test_probe.py /tmp/agb-probe-check/tests/
cd /tmp/agb-probe-check && uv sync && uv run pytest tests/test_probe.py -q; cd -
```
Expected: 14 passed.

Do not commit anything in the source repository, and do not modify it in any way. It is read-only evidence from a prior benchmark round.

- [ ] **Step 8: Record validation and clean up**

Write `probes/VALIDATION.md` with the command above, its actual output, the date, the source directory, and the scaffold commit SHA the working tree sits on (`git -C "$SRC" rev-parse --short HEAD`). Note explicitly that the target was an uncommitted working tree, so the SHA identifies the scaffold rather than the implementation. Then:

```bash
rm -rf /tmp/agb-probe-check
```

- [ ] **Step 9: Verify the case is complete and leaks nothing**

Run:
```sh
C=skills/agent-bench/cases/L-taskflow
ls $C/case.md $C/acceptance.md $C/rubric.md $C/spec/features.md $C/spec/CONVENTIONS.md $C/probes/SHA256SUMS $C/probes/VALIDATION.md $C/scaffold/BOOTSTRAP.md
grep -qF 'What this case does NOT measure' $C/case.md || echo "MISSING does-not-measure"
test ! -d $C/reference && echo "no reference solution committed"
cd $C/probes && shasum -a 256 -c SHA256SUMS; cd -
```
Expected: all files listed, `no reference solution committed`, and `test_probe.py: OK`.

- [ ] **Step 10: Commit**

```bash
git add skills/agent-bench/cases/L-taskflow
git commit -m "feat: port L-taskflow case from orq-lite benchmark

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Port L-hookrelay

**Files:** same nine paths as Task 10, under `skills/agent-bench/cases/L-hookrelay/`, plus:
- Create: `skills/agent-bench/cases/L-hookrelay/probes/PROBE_DEFECTS.md` (copy)

- [ ] **Step 1: Copy the ported material**

```bash
B=/Users/lionelchamorro/Projects/personal/orquesta-lite/benchmark/round2
C=skills/agent-bench/cases/L-hookrelay
mkdir -p $C/spec $C/scaffold $C/probes
cp $B/features.md         $C/spec/features.md
cp $B/CONVENTIONS.md      $C/spec/CONVENTIONS.md
cp $B/probe/test_probe.py $C/probes/test_probe.py
cp $B/probe/PROBE_DEFECTS.md $C/probes/PROBE_DEFECTS.md
```

The source probe carries three SHA files (`PROBE_SHA256`, `.v2.1`, `.v2.2`) recording its revision history. Copy only the current probe; the history is preserved by `PROBE_DEFECTS.md`, and `SHA256SUMS` is regenerated in the next step.

- [ ] **Step 2: Freeze the probe hash**

```bash
cd skills/agent-bench/cases/L-hookrelay/probes && shasum -a 256 test_probe.py > SHA256SUMS && cd -
```

- [ ] **Step 3: Write `scaffold/BOOTSTRAP.md`**

The dependency list is fixed by the spec's own "Stack (fixed — do not substitute)" preamble:

```sh
uv init --name hookrelay --python 3.12
uv add fastapi uvicorn "sqlalchemy[asyncio]" aiosqlite pydantic-settings httpx
uv add --dev pytest pytest-asyncio ruff
mkdir -p app tests && touch app/__init__.py tests/__init__.py
```

`httpx` is a **runtime** dependency here, not a dev one — it is the delivery client. Then the same `pyproject.toml` block as Task 10:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 100
```

and the same closing instruction: verify both gates green, then `git add -A && git commit -m "chore: bench scaffold" && git tag bench-base`.

- [ ] **Step 4: Write `acceptance.md`**

One item per observable criterion across the spec's sections. Round 4 evaluated Hookrelay at 30 items; reconcile against that count and state the frozen count at the top. If your walk yields a different count, record why in `case.md` under `## Provenance`.

- [ ] **Step 5: Write `rubric.md` and `case.md`**

Same structure as Task 10, with Hookrelay-specific anchors and `## What this case does NOT measure` naming context retention, defect detection in existing code, and codebase navigation.

- [ ] **Step 6: Validate the probes**

`hookrelay-r4-gpt-sol`'s work was never committed either — branch `bench-r4` points at the scaffold and the implementation is untracked. Copy the working tree, exactly as Task 10 does:

**Copy the source `.venv` and do not run `uv sync`.** Task 10's first fix attempt stalled for ten minutes because `uv sync` re-downloaded the dependency tree; reusing the existing virtualenv runs the probe in about ten seconds with no network. Invoke the interpreter directly — `uv run` would re-resolve.

```bash
SRC=/Users/lionelchamorro/Projects/personal/hookrelay-r4-gpt-sol
rm -rf /tmp/agb-hr-check
rsync -a --exclude '.git' --exclude '.orquestalite' --exclude '__pycache__' \
      --exclude '.pytest_cache' --exclude '.ruff_cache' \
      "$SRC/" /tmp/agb-hr-check/
cp skills/agent-bench/cases/L-hookrelay/probes/test_probe.py /tmp/agb-hr-check/tests/
cd /tmp/agb-hr-check && ./.venv/bin/python -m pytest tests/test_probe.py -q; cd -
```
Expected: 15 passed — `hookrelay-r4-gpt-sol` scored 15/15 on this probe in round 4.

Then, per `references/adding-a-case.md`, break exactly one requirement in the throwaway copy, re-run the same command, and confirm the corresponding probe test is the **only** failure. Both transcripts go in `probes/VALIDATION.md`.

Do not commit or modify anything in the source repository.

- [ ] **Step 7: Record validation and clean up**

Write `probes/VALIDATION.md` with the command, its actual output, the date, the source directory, and the scaffold SHA the working tree sits on — noting that the target was an uncommitted working tree. Then `rm -rf /tmp/agb-hr-check`.

- [ ] **Step 8: Verify**

Run the same completeness check as Task 10 Step 9, with `C=skills/agent-bench/cases/L-hookrelay`.
Expected: all files present, no reference solution, `test_probe.py: OK`.

- [ ] **Step 9: Commit**

```bash
git add skills/agent-bench/cases/L-hookrelay
git commit -m "feat: port L-hookrelay case from orq-lite benchmark round 2

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Phase C — New case families (Tasks 12-17)

### Task 12: S-ledger

**Files:**
- Create: `skills/agent-bench/cases/S-ledger/case.md`
- Create: `skills/agent-bench/cases/S-ledger/spec/features.md`
- Create: `skills/agent-bench/cases/S-ledger/spec/CONVENTIONS.md`
- Create: `skills/agent-bench/cases/S-ledger/scaffold/BOOTSTRAP.md`
- Create: `skills/agent-bench/cases/S-ledger/probes/test_probe.py`
- Create: `skills/agent-bench/cases/S-ledger/probes/SHA256SUMS`
- Create: `skills/agent-bench/cases/S-ledger/probes/VALIDATION.md`
- Create: `skills/agent-bench/cases/S-ledger/acceptance.md`
- Create: `skills/agent-bench/cases/S-ledger/rubric.md`

- [ ] **Step 1: Write `spec/features.md`**

One `##` section, sized for 15-45 minutes. The service, stated as a contract:

- `POST /accounts` `{"name": str}` → `201 {"id": str, "name": str, "balance_minor": 0, "created_at": iso8601-aware}`
- `POST /transfers` with header `Idempotency-Key: <str>`, body `{"from_account_id": str, "to_account_id": str, "amount_minor": int}` →
  - `201 {"id", "from_account_id", "to_account_id", "amount_minor", "created_at"}` on success
  - replaying the same `Idempotency-Key` with an identical body returns `200` and the **same transfer id**, and does not move money again
  - replaying the same `Idempotency-Key` with a different body returns `409`
  - missing header returns `400`
  - `amount_minor <= 0` returns `422`
  - insufficient balance returns `409 {"detail": "insufficient_funds"}`
  - unknown account returns `404`
- `GET /accounts/{id}` → `200` with the current `balance_minor`, or `404`
- `GET /accounts/{id}/transactions?limit=&offset=` → `200 {"items": [...], "total": int}`, newest first, `limit` default 20 and maximum 100, `limit > 100` returns `422`
- Balances are integer minor units. No floats anywhere in the money path.
- Every account starts at `balance_minor: 0`; a `POST /accounts/{id}/credit` `{"amount_minor": int > 0}` → `201` funds it.
- Timestamps are timezone-aware on the way out, including after a persistence round-trip.

Storage: SQLite via async SQLAlchemy 2.0. State that the suite must run without a live server, using an ASGI transport.

- [ ] **Step 2: Write `spec/CONVENTIONS.md`**

Start from `cases/L-taskflow/spec/CONVENTIONS.md` and cut anything that does not apply to a service with no background worker and no websocket. Keep the failure-mode rules about validation-bypassing write paths, partial updates, and timezone handling.

- [ ] **Step 3: Write `scaffold/BOOTSTRAP.md`**

```sh
uv init --name ledger --python 3.12
uv add fastapi "sqlalchemy[asyncio]" aiosqlite pydantic-settings
uv add --dev pytest pytest-asyncio httpx ruff
mkdir -p app tests && touch app/__init__.py tests/__init__.py
```

with the same `pyproject.toml` block and tag step as Task 10.

- [ ] **Step 4: Write the probes**

Black-box pytest against the ASGI app. Ten tests, one per contract clause that is cheap to get wrong:

1. `test_credit_then_balance` — credit 500, `GET` returns `balance_minor == 500`.
2. `test_transfer_moves_exact_minor_units` — after a 250 transfer, source is 250 and destination is 250; assert integers, not floats.
3. `test_idempotent_replay_same_body_returns_same_id_and_moves_once` — two identical `POST /transfers`; second is `200`, same id, balances unchanged from after the first.
4. `test_idempotent_replay_different_body_conflicts` — same key, changed amount → `409`.
5. `test_missing_idempotency_key_rejected` — `400`.
6. `test_non_positive_amount_rejected` — `0` and `-1` → `422`.
7. `test_insufficient_funds` — `409` and body `{"detail": "insufficient_funds"}`; assert balances unchanged.
8. `test_unknown_account` — `404` for both source and destination.
9. `test_pagination_bounds_and_order` — 25 transactions, default `limit` returns 20, `total` is 25, newest first, `limit=101` → `422`, `offset` past the end returns an empty list with the correct `total`.
10. `test_timestamps_are_timezone_aware_after_roundtrip` — `datetime.fromisoformat(created_at).tzinfo is not None` on a **re-fetched** record, not the creation response.

Test 10 exists because a naive-datetime round-trip loss is a defect that recurred across independent implementations in round 4.

- [ ] **Step 5: Validate the probes against a throwaway implementation**

Build a minimal correct implementation in `/tmp/agb-ledger-ref` (outside the repository), run the probes, confirm 10 passed. Then break exactly one criterion — remove the idempotency-key uniqueness check — and confirm tests 3 and 4 fail while the rest pass.

Run: `cd /tmp/agb-ledger-ref && uv run pytest tests/test_probe.py -q`
Expected, first pass: `10 passed`. Second pass, after the deliberate break: `2 failed, 8 passed`.

- [ ] **Step 6: Record validation, freeze, and delete the reference**

Write both outputs into `probes/VALIDATION.md`. Then:

```bash
cd skills/agent-bench/cases/S-ledger/probes && shasum -a 256 test_probe.py > SHA256SUMS && cd -
rm -rf /tmp/agb-ledger-ref
```

- [ ] **Step 7: Write `acceptance.md`, `rubric.md`, `case.md`**

`acceptance.md`: one row per contract clause above, each with a `curl` or pytest one-liner as `verification_command`. State the frozen item count.
`rubric.md`: the seven dimensions with ledger-specific anchors; drop concurrency to a low weight and say why in the file — there is no background work here.
`case.md`: `## What this case does NOT measure` must name background processing, websockets, cross-session context, and defect detection.

- [ ] **Step 8: Verify**

Run the Task 10 Step 9 completeness check with `C=skills/agent-bench/cases/S-ledger`, plus:
```sh
test ! -e /tmp/agb-ledger-ref && echo "reference deleted"
grep -c '^| ' skills/agent-bench/cases/S-ledger/acceptance.md
```
Expected: all files present, `reference deleted`, and an item count matching the number stated at the top of `acceptance.md`.

- [ ] **Step 9: Commit**

```bash
git add skills/agent-bench/cases/S-ledger
git commit -m "feat: S-ledger short greenfield case

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: S-ingest

**Files:** the same nine paths under `skills/agent-bench/cases/S-ingest/`.

- [ ] **Step 1: Write `spec/features.md`**

A CLI, not a service, so that "short" is not always the same shape.

`ingest --input <csv> --output <parquet> --quarantine <csv> [--strict]`

- Input columns: `id` (non-empty string, unique), `amount_minor` (integer), `currency` (exactly three uppercase letters), `occurred_at` (ISO-8601, timezone-aware).
- Valid rows are written to the parquet output preserving input order.
- Invalid rows are written to the quarantine CSV with the original columns plus a `reason` column naming the first failing rule, in the order the rules are listed above.
- A duplicate `id` quarantines the **later** occurrence, not the first.
- Exit code `0` when at least one row is valid, `1` when none are, and `2` when `--strict` is set and any row was quarantined.
- The process prints one summary line to stdout: `read=<n> valid=<n> quarantined=<n>`.
- An input file that does not exist exits `2` with a message on stderr and creates no output files.
- An empty input file (header only) exits `1`, writes an empty parquet with the correct schema, and an empty quarantine file with the header.

Dependencies: `polars` for the dataframe and parquet write, per the project Python rules.

- [ ] **Step 2: Write `scaffold/BOOTSTRAP.md`**

```sh
uv init --name ingest --python 3.12
uv add polars
uv add --dev pytest ruff
mkdir -p app tests && touch app/__init__.py tests/__init__.py
```

with the same `pyproject.toml` ruff block and tag step. `asyncio_mode` is not needed here; omit it.

- [ ] **Step 3: Write the probes**

Eight tests invoking the CLI as a subprocess, never importing internals:

1. `test_all_valid_rows_pass_through_in_order`
2. `test_bad_amount_quarantined_with_reason`
3. `test_bad_currency_quarantined_with_reason` — lowercase and four-letter both quarantined
4. `test_naive_timestamp_quarantined` — a timestamp without offset is invalid
5. `test_duplicate_id_quarantines_the_later_row` — assert the first survives
6. `test_first_failing_rule_wins` — a row bad in two ways reports the earlier rule
7. `test_exit_codes` — all three of `0`, `1`, `2` including `--strict`
8. `test_missing_and_empty_input` — missing file exits `2` and creates nothing; header-only exits `1` and writes both empty files with correct headers

- [ ] **Step 4: Validate, record, freeze**

Same procedure as Task 12 Steps 5-6, in `/tmp/agb-ingest-ref`. Deliberate break: make duplicate detection keep the later row instead of the first, and confirm only test 5 fails.
Expected, first pass: `8 passed`. After the break: `1 failed, 7 passed`.

- [ ] **Step 5: Write `acceptance.md`, `rubric.md`, `case.md`**

`rubric.md`: drop concurrency and websocket-flavoured anchors entirely; raise the weight of correctness and robustness to absorb them, and record the reweighting in the file.
`case.md`: `## What this case does NOT measure` names HTTP contract design, persistence, background work, and cross-session context.

- [ ] **Step 6: Verify**

Task 10 Step 9 completeness check with `C=skills/agent-bench/cases/S-ingest`, plus `test ! -e /tmp/agb-ingest-ref`.

- [ ] **Step 7: Commit**

```bash
git add skills/agent-bench/cases/S-ingest
git commit -m "feat: S-ingest short greenfield CLI case

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: Freeze the shared base

**Files:**
- Create: `skills/agent-bench/cases/_base-taskflow/BASE.md`
- Create: `skills/agent-bench/cases/_base-taskflow/tree/` (the frozen source tree)
- Modify: `docs/superpowers/specs/2026-08-07-agent-bench-design.md` (§3.1 and §5)

**Interfaces:**
- Produces: `_base-taskflow@1` — the base that Tasks 15 and 16 both build on. Its verification commands are cited by both.

The base is `taskflow-r4-gpt-sol` at branch `bench-r4`. It was chosen over the cheaper `taskflow-r4-oneshot` because its only confirmed finding is a design deviation — a module-level `_event_bus` instead of one scoped to `app.state` — with no observable test failure, whereas `oneshot` carries two functional defects (naive timestamps after an aiosqlite round-trip, and a crash on `DELETE` of a pending job caused by `assert job is not None` sitting outside the `try/except` around `execute`).

- [ ] **Step 1: Export the tree**

**`git archive` will not work here.** The source repository's `bench-r4` branch still points at the scaffold commit; the delivered implementation was never committed and lives untracked in the working tree. Copy the tree instead:

```bash
SRC=/Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol
mkdir -p skills/agent-bench/cases/_base-taskflow/tree
rsync -a --exclude '.git' --exclude '.orquestalite' --exclude '__pycache__' \
      --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude '.venv' \
      "$SRC/" skills/agent-bench/cases/_base-taskflow/tree/
ls skills/agent-bench/cases/_base-taskflow/tree
```
Expected: `app`, `tests`, `pyproject.toml`, `uv.lock`, `README.md`, `CONVENTIONS.md`, `features.md`, plus the orq-lite run configuration that Step 2 strips.

Never commit, stage, or otherwise modify the source repository. It is read-only evidence from a prior benchmark round, and its uncommitted working tree is the only copy of that round's artifact.

- [ ] **Step 2: Strip run state and benchmark residue**

```bash
cd skills/agent-bench/cases/_base-taskflow/tree
rm -rf .orquestalite .claude .superpowers docs prompts schemas flows.json team.json skills-lock.json
rm -f features.md CONVENTIONS.md
cd -
```

`features.md` and `CONVENTIONS.md` are removed because `B-sabotage` and `R-envelope` supply their own task framing; leaving the original build spec in the tree would hand a bug hunter the acceptance criteria for free.

- [ ] **Step 3: Verify the stripped tree still builds and passes its own suite**

```bash
cp -R skills/agent-bench/cases/_base-taskflow/tree /tmp/agb-base-check
cd /tmp/agb-base-check && uv sync && uv run ruff check . && uv run pytest -q; cd -
```
Expected: ruff exits 0; pytest reports 44 passed (the count recorded for this arm in round 4). If the count differs, stop and record the discrepancy in `BASE.md` before continuing.

- [ ] **Step 4: Verify the L-taskflow probe still scores 14/14 against the stripped tree**

```bash
cp skills/agent-bench/cases/L-taskflow/probes/test_probe.py /tmp/agb-base-check/tests/
cd /tmp/agb-base-check && uv run pytest tests/test_probe.py -q; cd -
rm -rf /tmp/agb-base-check
```
Expected: 14 passed.

- [ ] **Step 5: Write `BASE.md`**

Sections: `## Identity` (`_base-taskflow@1`), `## Provenance` — and here the provenance cannot be a commit SHA, because the source implementation was never committed. Record instead: the source directory, the scaffold commit its working tree sat on (`git -C "$SRC" rev-parse --short HEAD`), the date of the copy, and a content hash of the exported tree so the base is pinned and auditable:

```bash
cd skills/agent-bench/cases/_base-taskflow/tree && \
  find . -type f -not -path './.venv/*' | sort | xargs shasum -a 256 | shasum -a 256; cd -
```

State plainly that the round-4 artifact lived in an uncommitted working tree and that this copy is what pins it. Then `## Known deviations` (the module-level `_event_bus`, stated as a documented deviation so that a hunter reporting it is neither credited as finding a seeded defect nor penalised as a false positive), `## Verification` (the two command blocks above with their expected outputs), `## What was stripped` (the list from Step 2 and why), `## Staleness` (regenerating this base bumps it to `@2` and invalidates comparability of `B-sabotage` and `R-envelope` runs across the boundary).

One more section, `## Answer-key exposure`, stating verbatim:

> This tree is a complete working implementation of `L-taskflow`'s specification, and this repository is public. Keeping it here is a deliberate trade: families B and R need a realistic codebase, and building one from nothing would cost more than the exposure does. The consequence is recorded in `cases/L-taskflow/case.md` under "Validity threat: a public reference implementation exists". Do not resolve this by deleting the base; resolve it, if it ever matters, by moving B and R onto a codebase that corresponds to no case in the catalog.

- [ ] **Step 6: Amend the design spec**

In `docs/superpowers/specs/2026-08-07-agent-bench-design.md`:
- In §3.1, after the case layout block, add a paragraph: cases in families B and R share a frozen implementation stored at `cases/_base-taskflow/`, versioned as `_base-taskflow@<n>`, documented by its own `BASE.md`.
- In §5, add `_base-taskflow` to the table with family `shared base`, and note that `B-sabotage` and `R-envelope` both declare it.

- [ ] **Step 7: Verify size and that no state leaked**

Run:
```sh
du -sh skills/agent-bench/cases/_base-taskflow
find skills/agent-bench/cases/_base-taskflow -name '.orquestalite' -o -name 'team.json' -o -name 'features.md'
```
Expected: under 1 MB; the `find` prints nothing.

- [ ] **Step 8: Commit**

```bash
git add skills/agent-bench/cases/_base-taskflow docs/superpowers/specs/2026-08-07-agent-bench-design.md
git commit -m "feat: freeze _base-taskflow@1 shared base for B and R families

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 15: B-sabotage

**Files:**
- Create: `skills/agent-bench/cases/B-sabotage/case.md`
- Create: `skills/agent-bench/cases/B-sabotage/spec/brief.md`
- Create: `skills/agent-bench/cases/B-sabotage/defects/D0-control.md`
- Create: `skills/agent-bench/cases/B-sabotage/defects/D1/`, `D2/`, `D3/`, `D4/`, `D5/`, `D6/`, `D7/` — each containing `defect.md`, `patch.diff`, `detect.py`
- Create: `skills/agent-bench/cases/B-sabotage/defects/SHA256SUMS`
- Create: `skills/agent-bench/cases/B-sabotage/acceptance.md`
- Create: `skills/agent-bench/cases/B-sabotage/rubric.md`
- Create: `skills/agent-bench/cases/B-sabotage/probes/VALIDATION.md`

This case has no `scaffold/`; the working copy is `_base-taskflow@1` plus zero or more defect patches.

- [ ] **Step 1: Write `spec/brief.md`**

The prompt the solver receives. It must not reveal how many defects exist, or that there may be none:

> This service passes its own test suite and both gates. Audit it for defects that violate its documented behaviour. For every defect you report, provide a reproduction — a failing test, a request transcript, or a command with its observed output. Report only what you can reproduce.

Include the service's documented behaviour as an appendix in this file, derived from `cases/L-taskflow/spec/features.md`, so the hunter has a contract to audit against.

- [ ] **Step 2: Author the seven defects**

Each defect directory contains:
- `defect.md` — the criterion violated, the observable symptom, and the hunt-list category it belongs to
- `patch.diff` — applies cleanly to `_base-taskflow@1` with `git apply`
- `detect.py` — a pytest file that **fails** on the patched tree and **passes** on the unpatched tree. This is the ground truth for recall

The seven, each drawn from a defect pattern this project has actually observed:

| ID | Defect | Category |
|---|---|---|
| D1 | Model column loses `tzinfo` across the persistence round-trip | naive/aware datetime loss |
| D2 | An invariant `assert` sits outside the `try/except` meant to contain it, so a specific delete crashes the request | assertion outside error handling |
| D3 | Partial update overwrites unset fields with `None` | partial-update data loss |
| D4 | A stats aggregation groups by name instead of id | join on name instead of id |
| D5 | Pagination is off by one at the boundary — `offset` past the end returns the last page instead of an empty list | boundary math |
| D6 | An event is published inside the transaction, so a rollback still emits it | event published inside a transaction |
| D7 | An existence check is removed and the test covering it is weakened, so both gates stay green while an acceptance criterion is observably violated | weakened test |

D7 is the pattern already validated in `orquesta-lite/benchmark/context-metrics/` and is the most important of the seven: it is the only one that also tests whether the hunter distrusts a green suite.

- [ ] **Step 3: Verify every patch applies, keeps gates green, and is detected**

Run this loop once per defect, substituting `D1` through `D7` for `$d`:

```bash
R=$(git rev-parse --show-toplevel)
d=D1   # repeat for D2 D3 D4 D5 D6 D7
rm -rf /tmp/agb-def-check
cp -R "$R/skills/agent-bench/cases/_base-taskflow/tree" /tmp/agb-def-check
cd /tmp/agb-def-check
git init -q && git add -A && git commit -qm base
git apply "$R/skills/agent-bench/cases/B-sabotage/defects/$d/patch.diff"
uv sync
uv run ruff check . && uv run pytest -q            # must both still pass
cp "$R/skills/agent-bench/cases/B-sabotage/defects/$d/detect.py" tests/
uv run pytest tests/detect.py -q                    # must FAIL
cd - && rm -rf /tmp/agb-def-check
```

Expected per defect: `git apply` silent; ruff exit 0; the project suite passes; `detect.py` fails. **A defect whose patch turns a gate red is not usable — it would be found by running the gates rather than by hunting.** Rework it until the gates stay green.

- [ ] **Step 4: Verify each detector passes on the clean base**

```bash
R=$(git rev-parse --show-toplevel)
rm -rf /tmp/agb-clean-check
cp -R "$R/skills/agent-bench/cases/_base-taskflow/tree" /tmp/agb-clean-check
cd /tmp/agb-clean-check && uv sync
for d in D1 D2 D3 D4 D5 D6 D7; do
  cp "$R/skills/agent-bench/cases/B-sabotage/defects/$d/detect.py" "tests/detect_$d.py"
done
uv run pytest tests/detect_D*.py -q; cd - && rm -rf /tmp/agb-clean-check
```
Expected: 7 passed. A detector that fails on the clean base is testing the base's own behaviour, not the defect.

- [ ] **Step 5: Write `defects/D0-control.md`**

The zero-defect arm: the unpatched base. Its purpose is the false-positive denominator. State that at least one repetition per comparison must run D0, and that findings reported against D0 which reproduce are recorded as base defects — not false positives — and promoted into `_base-taskflow/BASE.md` as known deviations, bumping the base version.

- [ ] **Step 6: Write `acceptance.md`, `rubric.md`, `case.md`**

`acceptance.md` for this family is the scoring input rather than a checklist: define recall (`seeded defects reproduced by the hunter / seeded defects present`), precision (`reproduced findings / total findings`), and the false-positive rate from D0. Give the command that maps a hunter's finding to a seeded defect id: run that defect's `detect.py` against the tree the hunter examined and confirm the finding describes the same symptom.

`rubric.md`: the four report dimensions from `evaluator-4-judge.md` — evidence quality 40%, severity calibration 25%, actionability 20%, absence of padding 15% — with anchors.

`case.md`: `## What this case does NOT measure` names authoring ability, architecture, and cross-session context.

- [ ] **Step 7: Freeze and verify**

```bash
cd skills/agent-bench/cases/B-sabotage/defects && shasum -a 256 D*/patch.diff D*/detect.py > SHA256SUMS && shasum -a 256 -c SHA256SUMS; cd -
```
Expected: every line `OK`.

- [ ] **Step 8: Commit**

```bash
git add skills/agent-bench/cases/B-sabotage
git commit -m "feat: B-sabotage bug hunt case with seven seeded defects and a control arm

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 16: R-envelope

**Files:**
- Create: `skills/agent-bench/cases/R-envelope/case.md`
- Create: `skills/agent-bench/cases/R-envelope/spec/brief.md`
- Create: `skills/agent-bench/cases/R-envelope/sites.md`
- Create: `skills/agent-bench/cases/R-envelope/probes/test_probe.py`
- Create: `skills/agent-bench/cases/R-envelope/probes/SHA256SUMS`
- Create: `skills/agent-bench/cases/R-envelope/probes/VALIDATION.md`
- Create: `skills/agent-bench/cases/R-envelope/acceptance.md`
- Create: `skills/agent-bench/cases/R-envelope/rubric.md`

Working copy is `_base-taskflow@1`, unpatched.

- [ ] **Step 1: Write `spec/brief.md`**

The task: migrate every error response in the service to an RFC 7807 problem-details envelope — `application/problem+json` with `type`, `title`, `status`, `detail`, and `instance` — without changing any success response, and without breaking the existing suite. The brief states the required shape precisely and says the existing tests must be updated where they assert the old error shape, but no success-path test may change.

- [ ] **Step 2: Generate and seal the site list**

The sealed list must be reproducible by a command, not hand-curated, or coverage cannot be audited:

```bash
cd skills/agent-bench/cases/_base-taskflow/tree
grep -rn 'HTTPException\|JSONResponse\|status_code=4\|status_code=5' app/ | sort > /tmp/agb-sites.txt
wc -l /tmp/agb-sites.txt
```

Write `sites.md` containing the generating command, the resulting list with `file:line` and a one-line description per site, and the frozen total. State that a solver is never shown this file.

- [ ] **Step 3: Write the probes**

Black-box tests asserting the new envelope on every error class the service can produce — at minimum a 404, a 409, a 422, and a 500 path — checking the `application/problem+json` content type and all five required members, plus one test asserting a success response is byte-identical to the base behaviour.

- [ ] **Step 4: Validate**

Perform the migration yourself in `/tmp/agb-envelope-ref`, run the probes and the base suite, confirm all pass. Then revert one site and confirm the corresponding probe fails. Record both outputs in `probes/VALIDATION.md` and delete the reference.

- [ ] **Step 5: Write `acceptance.md`, `rubric.md`, `case.md`**

`acceptance.md` defines the three scoring inputs: `site_coverage` (sites migrated over the sealed total, verified by re-running the generating command against the solver's tree and diffing), `regression_free` (base suite plus probes, all-or-nothing), and `scope_creep_ratio` (files touched outside the sealed site list over files touched, from `git diff --name-only`).

`case.md`: `## What this case does NOT measure` names greenfield design, defect detection, and cross-session context. `## What it measures` names codebase navigation and sweep completeness, and notes this is the case where subagent strategies should separate from single-session ones.

- [ ] **Step 6: Verify**

Run:
```sh
C=skills/agent-bench/cases/R-envelope
ls $C/case.md $C/sites.md $C/acceptance.md $C/rubric.md $C/probes/SHA256SUMS $C/probes/VALIDATION.md
grep -qF 'grep -rn' $C/sites.md || echo "MISSING generating command"
cd $C/probes && shasum -a 256 -c SHA256SUMS; cd -
```
Expected: all files present, no `MISSING` line, `test_probe.py: OK`.

- [ ] **Step 7: Commit**

```bash
git add skills/agent-bench/cases/R-envelope
git commit -m "feat: R-envelope multi-file refactor case with sealed site list

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 17: M-relay

**Files:**
- Create: `skills/agent-bench/cases/M-relay/case.md`
- Create: `skills/agent-bench/cases/M-relay/spec/leg-1.md`
- Create: `skills/agent-bench/cases/M-relay/spec/leg-2.md`
- Create: `skills/agent-bench/cases/M-relay/spec/leg-3.md`
- Create: `skills/agent-bench/cases/M-relay/continuity.md`
- Create: `skills/agent-bench/cases/M-relay/scaffold/BOOTSTRAP.md`
- Create: `skills/agent-bench/cases/M-relay/probes/test_probe.py`
- Create: `skills/agent-bench/cases/M-relay/probes/SHA256SUMS`
- Create: `skills/agent-bench/cases/M-relay/probes/VALIDATION.md`
- Create: `skills/agent-bench/cases/M-relay/acceptance.md`
- Create: `skills/agent-bench/cases/M-relay/rubric.md`

**Interfaces:**
- Consumes: `cases/S-ledger` spec, scaffold, and probes from Task 12.

- [ ] **Step 1: Split the S-ledger contract into three legs**

- `leg-1.md`: accounts and credit. Requires the solver to make and record design decisions that later legs depend on — the money representation, the id scheme, and the error-body shape. The brief explicitly asks the solver to record these decisions wherever it normally would.
- `leg-2.md`: transfers with idempotency. Written so it can be implemented consistently **only** if leg 1's decisions are recalled; it never restates them.
- `leg-3.md`: paginated transaction history and the timezone-aware round-trip guarantee. Same property.

Each leg is a separate solver session with cold context. State in `case.md` that the harness must not carry conversation state between legs; only the repository and whatever persistence mechanism the arm under test provides may cross the boundary. That mechanism is the independent variable.

- [ ] **Step 2: Write `continuity.md`**

The sealed checklist scored at the end. One row per leg-1 decision that legs 2 and 3 must honour, each with a verification command. At minimum: money is integer minor units everywhere; the id scheme is unchanged; the error body shape is unchanged; no leg-1 endpoint contract was altered. State that a solver never sees this file.

- [ ] **Step 3: Write scaffold and probes**

`scaffold/BOOTSTRAP.md` is the S-ledger bootstrap verbatim. The probe is the S-ledger probe, re-frozen under this case's own `SHA256SUMS`, since the final state of leg 3 is the full S-ledger contract.

```bash
cp skills/agent-bench/cases/S-ledger/probes/test_probe.py skills/agent-bench/cases/M-relay/probes/test_probe.py
cd skills/agent-bench/cases/M-relay/probes && shasum -a 256 test_probe.py > SHA256SUMS && cd -
```

`probes/VALIDATION.md` cites the S-ledger validation by reference and records that the probe is unmodified — verify with:

```bash
diff skills/agent-bench/cases/S-ledger/probes/test_probe.py skills/agent-bench/cases/M-relay/probes/test_probe.py && echo identical
```
Expected: `identical`.

- [ ] **Step 4: Write `acceptance.md`, `rubric.md`, `case.md`**

`acceptance.md` defines the four scoring inputs: `final_outcome` (the L/S formula over leg 3's tree), `continuity` (share of `continuity.md` rows honoured), `rework_ratio` (lines rewritten of already-delivered work, from `git diff` between leg boundaries, over total lines delivered), and rediscovery cost — **reported only, not scored**, with a one-line note that the common-core token metrics already capture it.

`case.md`: `## What it measures` names cross-session continuity. `## What this case does NOT measure` names greenfield scale, defect detection, and codebase navigation. Add a `## Required arm structure` section stating that a memory-mechanism comparison must run both arms with identical leg prompts and identical cold-context handling, differing only in the mechanism.

- [ ] **Step 5: Verify**

Run:
```sh
C=skills/agent-bench/cases/M-relay
ls $C/spec/leg-1.md $C/spec/leg-2.md $C/spec/leg-3.md $C/continuity.md $C/acceptance.md $C/rubric.md
grep -qF '## Required arm structure' $C/case.md || echo "MISSING arm structure"
cd $C/probes && shasum -a 256 -c SHA256SUMS; cd -
```
Expected: all files present, no `MISSING` line, `test_probe.py: OK`.

- [ ] **Step 6: Commit**

```bash
git add skills/agent-bench/cases/M-relay
git commit -m "feat: M-relay multi-session continuity case

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Phase D — Ship (Task 18)

### Task 18: Catalog reconciliation, install verification, and first push

**Files:**
- Modify: `skills/agent-bench/cases/CATALOG.md`
- Modify: `README.md`

- [ ] **Step 1: Reconcile the catalog against what was actually built**

Every case directory must appear in `CATALOG.md` with its real frozen counts, and every catalog row must correspond to a directory.

Run:
```sh
ls -d skills/agent-bench/cases/*/ | sed 's|.*/cases/||;s|/||' | sort > /tmp/agb-dirs.txt
grep -oE '^\| `?[A-Z_]-?[a-z-]+' skills/agent-bench/cases/CATALOG.md | tr -d '|` ' | sort > /tmp/agb-rows.txt
diff /tmp/agb-dirs.txt /tmp/agb-rows.txt
```
Expected: the only difference is `_base-taskflow`, which is a shared base and not a case. If the catalog does not list it separately, add a `## Shared bases` section naming it.

- [ ] **Step 2: Verify every case satisfies the layout contract**

Run:
```sh
for c in L-taskflow L-hookrelay S-ledger S-ingest B-sabotage R-envelope M-relay; do
  p="skills/agent-bench/cases/$c"
  for f in case.md acceptance.md rubric.md; do
    test -f "$p/$f" || echo "MISSING $p/$f"
  done
  grep -qF 'What this case does NOT measure' "$p/case.md" || echo "MISSING does-not-measure in $c"
done
```
Expected: no output.

- [ ] **Step 3: Verify no reference solution or answer key was committed**

Run:
```sh
find skills/agent-bench/cases -type d -name reference
git ls-files skills/agent-bench/cases | grep -E '/(reference|solution)/' 
```
Expected: no output from either.

- [ ] **Step 4: Verify the skill folder is self-contained**

Every path the skill references at runtime must resolve inside `skills/agent-bench/`.

Run:
```sh
grep -rhoE '\b(references|templates|cases)/[A-Za-z0-9._/-]+' skills/agent-bench --include='*.md' \
  | sort -u | while read -r p; do
      test -e "skills/agent-bench/$p" || echo "DANGLING $p"
    done
```
Expected: no `DANGLING` lines. Fix any that appear before pushing.

- [ ] **Step 5: Push**

```bash
git push -u origin main
```

- [ ] **Step 6: Verify the install path end to end**

```bash
npx skills add collectiveai-team/agent-bench
ls ~/.agents/skills/agent-bench/SKILL.md
ls ~/.agents/skills/agent-bench/cases
ls ~/.claude/skills/agent-bench
```
Expected: `SKILL.md` present, all seven case directories plus `_base-taskflow` present, and the symlink resolving in `~/.claude/skills/`.

If the case directories did not come along, the CLI is copying selectively; in that case record the actual behaviour in `README.md` under a `## Install caveats` section and add the fallback instruction to clone the repository and point `$AGENT_BENCH_HOME` at it.

- [ ] **Step 7: Update `README.md` with the verified install result**

State what the install actually produced, and the `$AGENT_BENCH_HOME` fallback for the run ledger.

- [ ] **Step 8: Commit and push**

```bash
git add README.md skills/agent-bench/cases/CATALOG.md
git commit -m "docs: reconcile catalog and record verified install behaviour

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push
```

---

## Post-plan: first real round

Not part of this plan, but the natural next step and the thing that will expose whatever is wrong with it: run one comparison end to end on `S-ledger` with N=5 — it is the cheapest case and exercises all five phases and all four evaluator stages. The `correctness_normalized` weights for families B, R and M are labelled first-round defaults precisely so they can be revised after that round.
