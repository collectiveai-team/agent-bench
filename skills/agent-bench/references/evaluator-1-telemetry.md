# Evaluator — Stage 1: Telemetry

## Purpose

Produce a complete `telemetry.json` for one solver run. This is a mechanical extraction stage: every number comes from a log file or a git command. No LLM judgment, no code reading, no quality opinions.

## Inputs

| Item | Description |
|---|---|
| `manifest.json` | Written before the solver launched; records `run_id`, `base_commit_sha`, `telemetry.source_logs`, solver configuration, and `environment.provider_incidents` |
| Raw solver log(s) | Path(s) listed in `manifest.json` under `telemetry.source_logs` |

## Procedure

### 1. Identify the stream format

Inspect the raw log and consult `manifest.json.solver`:
- **Claude Code** — one JSON object per line; look for `"type":"result"`.
- **Codex** — one JSON object per line; look for `"type":"turn.completed"`.
- **opencode** — one JSON object per line; look for `"type":"step_finish"`.

For orq-lite runs, each invocation has its own `stdout.log` under `.orquestalite/runs/<run_id>/agents/<activity>/<invocation>/`. Select the parser by `meta.json.provider`: `"claude"` → Claude Code parser; `"codex"` → Codex parser; anything else → opencode parser.

### 2. Extract token counts and cost

Apply the extraction rules in `references/telemetry.md` exactly for the identified format:
- **Claude Code**: read the single `type == "result"` record. Set `cost_basis: "reported_by_provider"`.
- **Codex**: apply all three corrections — subtract `cached_input_tokens` from `input_tokens`, add `reasoning_output_tokens` to `output_tokens`, compute cost from token counts. Set `cost_basis: "computed_from_token_counts"` and fill `cost_basis_note` with the model name, rates used, and retrieval date.
- **opencode**: sum all `step_finish` events; apply the tool-event de-duplication rule. Set `cost_basis: "reported_by_provider"`.

### 3. Fill `totals` and `by_role`

For orq-lite runs, group invocation directories by role using the directory-name regex from `references/telemetry.md`. Sum each group's fields into one `by_role[]` row. Sum all rows into `totals`.

For single-agent runs (no orq-lite), `by_role` has one row with `role` taken from the solver identifier.

`totals.attempts` counts invocations where the attempt index (regex group 3) is greater than 1. `totals.agent_invocations` is the total count of all invocation directories processed.

### 4. Compute wall-clock net of rate limits

Set `totals.wall_clock_seconds` from the raw elapsed time. Set `totals.wall_clock_seconds_net_of_rate_limits` by subtracting:
1. Durations of any `manifest.environment.provider_incidents` that overlap the run window.
2. Durations of `type == "rate_limit_event"` pauses found in Claude Code streams.

`totals.rate_limit_events` is the count of such lines.

### 5. Set `convergence`

| Condition | Value |
|---|---|
| Run completed normally | `"converged"` |
| Budget ceiling reached | `"aborted_on_budget"` |
| Human intervened or run halted manually | `"required_human_intervention"` |

### 6. Compute `process_hygiene`

Run against the solver's branch at the evaluated SHA:

```sh
git diff --shortstat <base_commit_sha>...HEAD
git rev-list --count <base_commit_sha>..HEAD
```

Parse the output and fill `diff_lines_added`, `diff_lines_removed`, `files_touched`, and `commits`.

### 7. Verify arm identity

Before finalising, assert the run matches the manifest:
- **MCP arms** — assert the `n_mcp_servers` count (from `len(.mcp_servers)` in the `type == "system" subtype == "init"` record) matches the intent in the manifest. A zero count when MCP was intended means the server failed to start; the run is invalid.
- **Model arms** — assert `meta.json.model` in every invocation directory matches `manifest.solver.model`. A mismatch means the runtime fell back; stop and report.

## Output contract

Produce `telemetry.json` matching the template at `skills/agent-bench/templates/telemetry.json`. Field names must be exact:

`run_id`, `source_logs[]`, `totals.input_tokens`, `totals.output_tokens`, `totals.reasoning_tokens`, `totals.cache_read_tokens`, `totals.cache_write_tokens`, `totals.cost_usd`, `totals.wall_clock_seconds`, `totals.wall_clock_seconds_net_of_rate_limits`, `totals.agent_invocations`, `totals.turns`, `totals.attempts`, `totals.rate_limit_events`, `by_role[].role`, `by_role[].provider`, `by_role[].model`, `by_role[].invocations`, `by_role[].input_tokens`, `by_role[].output_tokens`, `by_role[].cache_read_tokens`, `by_role[].cache_write_tokens`, `by_role[].cost_usd`, `by_role[].duration_seconds`, `convergence`, `process_hygiene.commits`, `process_hygiene.diff_lines_added`, `process_hygiene.diff_lines_removed`, `process_hygiene.files_touched`, `cost_basis`, `cost_basis_note`.

## Refusals

- Never read the source tree to form an opinion.
- Never take a cost or token count from the agent's own prose summary.
- Never extrapolate or estimate a field; record `0` and note the gap in `cost_basis_note` when a field cannot be determined.
- Never compare a Codex computed cost against a Claude provider-reported cost without documenting the basis difference.

---

## Subagent brief

You are Stage 1 of a four-stage blind evaluator for an agent benchmark. Your sole job is to produce `telemetry.json` for one solver run. You extract numbers from log files — you do not read the solver's source code, form quality opinions, or accept figures from the agent's own prose.

**Inputs you have:**
- `manifest.json` — written before the solver launched; contains `run_id`, `base_commit_sha`, `telemetry.source_logs`, `solver` configuration, and `environment.provider_incidents`.
- Raw solver log(s) at the path(s) in `manifest.json.telemetry.source_logs`.

**Step 1 — Identify the stream format.**
Inspect the log. Determine whether it is a Claude Code stream (look for `"type":"result"`), a Codex stream (look for `"type":"turn.completed"`), or an opencode stream (look for `"type":"step_finish"`). For orq-lite runs, each invocation has its own `stdout.log` under `.orquestalite/runs/<run_id>/agents/<activity>/<invocation>/`; select the parser by `meta.json.provider`.

**Step 2 — Extract token counts and cost.**
Apply the rules in `references/telemetry.md` for the identified format. For Codex, apply all three corrections: (1) `totals.input_tokens = .usage.input_tokens - .usage.cached_input_tokens`, (2) `totals.output_tokens = .usage.output_tokens + .usage.reasoning_output_tokens`, (3) compute cost from token counts and record the model, rates, and retrieval date in `cost_basis_note`. Set `cost_basis: "computed_from_token_counts"`. For Claude Code and opencode, set `cost_basis: "reported_by_provider"`.

**Step 3 — Fill `totals` and `by_role`.**
For orq-lite runs, group invocations by role using the regex `^([a-z_0-9]+)\.c(\d+)\.a(\d+)(?:\.r(\d+))?$`. Sum each role group into one `by_role[]` row. Sum all rows into `totals`. For single-agent runs, `by_role` has one row.

**Step 4 — Compute wall-clock net of rate limits.**
`totals.wall_clock_seconds`: raw elapsed time. `totals.wall_clock_seconds_net_of_rate_limits`: subtract (a) durations of `manifest.environment.provider_incidents` overlapping the run window, and (b) durations of `type == "rate_limit_event"` pauses (Claude Code only).

**Step 5 — Set `convergence`.**
`"converged"` if normal completion; `"aborted_on_budget"` if a budget ceiling was hit; `"required_human_intervention"` if a human intervened.

**Step 6 — Compute `process_hygiene`.**
```sh
git diff --shortstat <base_commit_sha>...HEAD
git rev-list --count <base_commit_sha>..HEAD
```
Fill `diff_lines_added`, `diff_lines_removed`, `files_touched`, and `commits`.

**Step 7 — Verify arm identity.**
Assert `meta.json.model` in every invocation matches `manifest.solver.model`. For MCP arms, assert the MCP server count matches the manifest's intent. If either assertion fails, stop and report the mismatch — do not produce a `telemetry.json`.

**Output:** Write `telemetry.json` using the template at `skills/agent-bench/templates/telemetry.json`. Use those exact field names. Record `0` and add a note in `cost_basis_note` for any field that cannot be determined from logs.
