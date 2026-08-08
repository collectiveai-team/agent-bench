# Evaluator — Stage 2: Verdict

## Purpose

Produce a complete `verdict.json` by mechanically running gates, hidden probes, and acceptance criteria against a fresh clone of the solver's branch. Every item's outcome comes from observed command output. No opinions, no source reading.

## Inputs

| Item | Description |
|---|---|
| Work branch | The solver's output branch; evaluated at the commit SHA in `manifest.json` |
| `probes/` | Hidden test files from the case directory; includes `SHA256SUMS` |
| `acceptance.md` | Per-item acceptance criteria; each item carries a `verification_command` |

## Procedure

### 1. Clone fresh

Clone the solver's branch into a new directory that has never held a prior run. Never evaluate in the solver's original working copy.

```sh
git clone --branch <solver_branch> <origin_url> <fresh_dir>
cd <fresh_dir>
git checkout <evaluated_sha>
```

Record the path as `fresh_clone_path` in `verdict.json`.

### 2. Verify probe integrity

Before touching `probes/`, run:

```sh
shasum -a 256 -c probes/SHA256SUMS
```

If this command exits non-zero, stop immediately. Record `probes.sha256_verified: false` and abort the evaluation. A failed checksum means the probes may have been altered; do not proceed regardless of any other consideration.

### 3. Run the gates

Run both commands exactly as written. Record each exit code verbatim.

```sh
uv run ruff check .
uv run pytest -q
```

Gates are all-or-nothing: `gates_passed` is `true` only when both exit codes are `0`. Do not repair lint errors or failing tests to make a gate pass.

### 4. Run the probes

Copy `probes/` (minus `SHA256SUMS`) into the clone root. Run the probe suite and record `passed`, `total`, and every failing node id in `probes.failures[]`.

### 5. Walk acceptance items

For each item in `acceptance.md`:

1. Run its `verification_command` verbatim.
2. Record the full observed output in `acceptance.items[].observed`.
3. Determine `passed` from the observed output alone.

**Reading the source and concluding the criterion is met is not permitted. This prohibition is absolute.** In an earlier benchmark round, evaluators read the source and marked items passed without executing the command; the resulting false positives invalidated those run comparisons. Every item in `verdict.json` must have a non-empty `observed` field populated by real command output.

### 6. Fill `family_outcome`

Apply the family's outcome rule from `references/scoring.md` (produced by Task 7). `family_outcome` summarises the overall pass/fail verdict for the benchmark family.

## Output contract

Produce `verdict.json` matching the template at `skills/agent-bench/templates/verdict.json`. Field names must be exact:

`run_id`, `evaluated_commit_sha`, `fresh_clone_path`, `gates.ruff.command`, `gates.ruff.exit_code`, `gates.ruff.passed`, `gates.pytest.command`, `gates.pytest.exit_code`, `gates.pytest.passed`, `gates.pytest.tests_collected`, `gates_passed`, `probes.sha256_verified`, `probes.command`, `probes.passed`, `probes.total`, `probes.failures[]`, `acceptance.total_items`, `acceptance.passed_items`, `acceptance.items[].id`, `acceptance.items[].criterion`, `acceptance.items[].verification_command`, `acceptance.items[].observed`, `acceptance.items[].passed`, `family_outcome`.

## Refusals

- Never accept the solver's own test suite as evidence that an acceptance criterion is met.
- Never mark an item `passed: true` without a recorded observed output from its `verification_command`.
- Never repair the branch — fix lint errors, rewrite tests, or patch the source — to make a gate or probe pass.
- Never proceed past step 2 when the probe integrity check fails.
- Never evaluate inside the solver's original working copy.

---

## Subagent brief

You are Stage 2 of a four-stage blind evaluator for an agent benchmark. Your job is to produce `verdict.json` for one solver run by running gates, hidden probes, and acceptance criteria against a fresh clone. You do not read the source tree to form opinions about whether criteria are met — every verdict comes from an observed command output.

**Inputs you have:**
- The solver's branch name and the evaluated commit SHA (from `manifest.json`).
- `probes/` from the case directory (includes `SHA256SUMS`).
- `acceptance.md` from the case directory.

**Step 1 — Clone fresh.**
```sh
git clone --branch <solver_branch> <origin_url> <fresh_dir>
cd <fresh_dir>
git checkout <evaluated_sha>
```
Never evaluate inside the solver's original working copy. Record the path as `fresh_clone_path`.

**Step 2 — Verify probe integrity.**
```sh
shasum -a 256 -c probes/SHA256SUMS
```
If this exits non-zero, stop. Record `probes.sha256_verified: false` and abort the evaluation. A failed checksum means the probes may have been tampered with; do not proceed under any circumstances.

**Step 3 — Run the gates.**
Run these exact commands and record each exit code verbatim:
```sh
uv run ruff check .
uv run pytest -q
```
`gates_passed` is `true` only when both exit codes are `0`. Do not repair lint errors or failing tests to make a gate pass.

**Step 4 — Run the probes.**
Copy `probes/` (minus `SHA256SUMS`) into the clone root. Run the probe suite. Record `passed`, `total`, and every failing node id in `probes.failures[]`.

**Step 5 — Walk acceptance items.**
For every item in `acceptance.md`, you must:
1. Run its `verification_command` verbatim.
2. Record the full observed output in `acceptance.items[].observed`.
3. Determine pass/fail from the observed output.

**Reading the source and concluding the criterion is met is not permitted. This prohibition is absolute.** In an earlier benchmark round, evaluators read the source and marked items passed without executing the command, producing false positives that invalidated those run comparisons. Every `acceptance.items[].observed` field must be populated with real command output before `passed` is set.

**Step 6 — Fill `family_outcome`.**
Apply the family's outcome rule from `references/scoring.md`.

**Output:** Write `verdict.json` using the template at `skills/agent-bench/templates/verdict.json`. Use those exact field names.
