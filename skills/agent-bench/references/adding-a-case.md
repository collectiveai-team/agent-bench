# Adding a case

This guide is the authoring contract for every benchmark case. Tasks 10-17 implement cases against it. Every section below is required; deviating from the layout or omitting a required section breaks the evaluator pipeline.

## Layout

A case lives under `cases/<ID>/`. The directory separates material the solver sees from material it must never see.

```
cases/<ID>/
  case.md            # Identity, measures, gates, provenance
  spec/              # Task specification — copied into the solver's working copy
  scaffold/          # Starter code — copied into the solver's working copy
  acceptance.md      # Per-item acceptance criteria with verification commands
  rubric.md          # Judge rubric: 1/3/5 anchors per dimension; may reweight but must not add or remove dimensions — the set is fixed in evaluator-4-judge.md
  probes/            # Hidden test files; never copied into the solver's working copy
    test_probe.py    # One or more probe files
    SHA256SUMS       # Integrity manifest; frozen before any solver runs
    VALIDATION.md    # Probe validation record
```

`spec/` and `scaffold/` are the only directories copied into the solver's working copy. `probes/`, `acceptance.md`, and `rubric.md` are evaluation material; they are never placed within the solver's reach. See `references/run-protocol.md` for the exact copy procedure and the pre-flight verification command.

`rubric.md` may adjust the 1/3/5 score anchors and reweight the dimensions defined in `references/evaluator-4-judge.md`, but it must not add or remove dimensions. The dimension set is fixed by the evaluator. A dimension with missing anchors is silently skipped by Stage 4 — so adding an undocumented dimension does not raise an error, it simply produces no score for that dimension.

## case.md required sections

Every `case.md` must contain exactly these ATX-headed sections, in this order:

```markdown
# <ID>

## Identity

| Field | Value |
|---|---|
| Family | L / S / B / R / M |
| Version | 1 |
| Expected duration | ... |
| Expected cost | ... |

## What it measures

## What this case does NOT measure

## Gates

## Provenance
```

**`## Identity`** records the family, the case version (`<n>` — increment on any change to `probes/`, `acceptance.md`, `rubric.md`, or `spec/`), the expected solver duration range, and the expected cost range. These are authoring-time estimates; update them when evidence from multiple runs disagrees materially.

**`## What it measures`** — one paragraph naming the specific skills or behaviors this case can distinguish between arms. Be concrete: "idempotency key handling, boundary math on balances, and structured error response bodies."

**`## What this case does NOT measure`** — what a good score on this case does **not** mean. Derive this honestly from the family: greenfield cases start from an empty tree and cannot measure codebase navigation, defect detection, or cross-session continuity; `B` cases score findings reports and cannot measure authoring capability or architecture; `R` cases score refactors over a sealed site list and cannot measure greenfield design or defect detection; `M` cases measure continuity across legs and cannot measure greenfield scale or codebase navigation. Stating this explicitly is how a framer knows whether to reach for a different case before running an experiment.

**`## Gates`** — the two commands that must both exit 0 before any evaluation proceeds:

```sh
uv run ruff check .
uv run pytest -q
```

These gates are identical for all cases and enforced by Stage 2 of the evaluator. No additional gates are permitted; gate divergence across cases would make cross-case comparisons ambiguous.

**`## Provenance`** — record the origin: whether the case is new or ported, the upstream source if ported, the author's identity or reference, and a brief version history.

## Writing acceptance criteria

`acceptance.md` holds the observable acceptance criteria that Stage 2 of the evaluator runs verbatim. Every item must appear as a row in a three-column Markdown table with these exact column headers:

```markdown
| id | criterion | verification_command |
|---|---|---|
| AC-01 | ... | ... |
```

The evaluator reads `id`, `criterion`, and `verification_command` from each row, runs the command in the root of a fresh clone of the solver's branch, records the observed output, and determines `passed` from that output alone. No source reading is permitted.

**Rules:**

- Every criterion must describe observable behavior: "running X produces Y." The phrase "the code should" is forbidden — it describes source text, not a runtime outcome.
- Every `verification_command` must be a single shell command the evaluator can run verbatim in the repository root of a fresh clone of the solver's branch. It must produce deterministic, machine-readable output. Prefer short `curl` or CLI invocations that emit an observable exit code or one-line output. Avoid embedding acceptance logic in a separate test file: `spec/` and `scaffold/` are visible to the solver, and adding a pytest acceptance module there would expose the criteria it is built to satisfy.
- IDs must be unique within the case and stable across case versions. Use the prefix `AC-` followed by a zero-padded two-digit integer.
- If the pass/fail match rule is not self-evident from the output, add an explanatory note row (`| note | ... | — |`) immediately below the item.

**Good example:**

| id | criterion | verification_command |
|---|---|---|
| AC-01 | `POST /transfer` with a missing `amount` field returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/transfer -H 'Content-Type: application/json' -d '{}'` |

The command runs, produces `422`, and the criterion is falsifiable: any other status code fails the item.

**Bad example (near-miss):**

| id | criterion | verification_command |
|---|---|---|
| AC-01 | The transfer endpoint validates that `amount` is present before writing. | `grep -r 'amount' src/routes/` |

This sounds checkable but is not. A passing grep confirms only that the string `amount` appears somewhere in the source tree — it passes even if the validation is absent or the handler returns 200 for a missing field. It tests what the code *says*, not what the running service *does*.

## Writing probes

Probes are hidden test files that Stage 2 of the evaluator copies into the solver's working copy and runs. They provide a more granular correctness signal than acceptance criteria and are not visible to the solver during the run.

**Probes must be written before any implementation is seen.** This is the load-bearing rule. Probes written after seeing an implementation test what that implementation happens to do, not what the spec requires. The failure it prevents is concrete: a probe tuned to a reference implementation's internal structure or quirks will pass that implementation and fail a correct-but-differently-structured one, producing a false negative that invalidates the comparison.

Probes are black-box: they exercise the contract through its public surface — HTTP endpoints, CLI entry points, importable public functions — and never import internal modules or read implementation files.

Freeze probes before any solver run. For a single probe file:

```sh
cd probes && shasum -a 256 test_probe.py > SHA256SUMS
```

For multiple probe files:

```sh
cd probes && shasum -a 256 *.py > SHA256SUMS
```

Stage 2 of the evaluator verifies the checksum with `shasum -a 256 -c probes/SHA256SUMS` before running the probes. A non-zero exit code aborts the evaluation immediately. Never alter `SHA256SUMS` after a solver has run against this case version; update it only when you increment the case version.

## Validating probes without shipping a solution

Before the case is used in any benchmark run, confirm that the probes correctly distinguish passing from failing behavior.

1. Build a throwaway reference implementation **outside the repository** in a temporary directory that is not tracked and will not be committed. The case spec in `spec/` is your only guide.
2. Run the probe suite against it:
   ```sh
   cd probes && uv run pytest -q
   ```
   Confirm all probes pass.
3. Break one requirement deliberately in the throwaway implementation: comment out a validation, reverse a condition, drop a required field from the response.
4. Run the probe suite again. Confirm the corresponding probe fails — and that only probes tied to the broken requirement fail.
5. Record both runs in `probes/VALIDATION.md`: the full-pass transcript and the targeted-failure transcript.
6. Delete the throwaway implementation entirely.

**The reference implementation is never committed.** A committed solution is a copyable answer key — a solver that reads `cases/` can trivially reproduce it, invalidating any comparison that arm participates in.

There is exactly one documented exception to this rule in this repository: `cases/_base-taskflow/`, which is a frozen good implementation of `L-taskflow` that families B and R depend on structurally. It was accepted deliberately because `B-sabotage` applies defect patches to it and `R-envelope` refactors it — both families require a stable, known-good starting point. It is named here so that it is not read as precedent; no other case adds a committed reference implementation.

## Probe defect log

When a probe is discovered to be wrong after the case is in use (for example, the probe passes incorrect behavior or fails correct behavior):

1. Fix the probe file.
2. Bump the case `Version` field in `case.md` `## Identity`.
3. Regenerate `SHA256SUMS` to reflect the fixed file.
4. Append a record to `probes/VALIDATION.md` containing:
   - What was wrong and how it was detected.
   - Whether any earlier runs were affected and, if so, how comparisons should be treated.
   - Which version the fix lands in.

This follows the precedent of `orquesta-lite/benchmark/round2/probe/PROBE_DEFECTS.md`. The log is permanent; do not delete or edit prior entries.

## Scaffold

The scaffold is the starting tree the solver receives. It must satisfy three invariants before any arm is launched.

**Bootstrap to green gates.** `uv run ruff check .` and `uv run pytest -q` must both exit 0 at scaffold HEAD. The run protocol checks this as part of the pre-flight checklist and will not proceed if either gate is red. A scaffold that ships with failing tests or lint errors corrupts every run started from it.

**Contain no hint of the solution.** The scaffold may set up package structure, type stubs, dependency declarations, and an empty or trivially-passing test suite. It must not contain any implementation code that gives away the required behavior, data structures that reflect the answer, or comments that describe what the solver needs to build.

**Be committed and tagged.** The scaffold commit SHA is what `manifest.base_commit_sha` records. The run protocol starts every arm from a clean base at that SHA, so the scaffold must be a stable, named commit — not a dirty working tree or an uncommitted patch.

Verify before any arm is launched (run in the solver's working copy root):

```sh
test ! -e probes && test ! -e acceptance.md && test ! -e rubric.md && echo "clean"
```

Both gates must be green and this command must print `clean`. See `references/run-protocol.md` for the full pre-flight checklist.
