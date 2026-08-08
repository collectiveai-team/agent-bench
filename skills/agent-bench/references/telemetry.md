# Telemetry Extraction Reference

Procedure guide for filling every field in `templates/telemetry.json`. Sections cover the three stream formats that `stdout.log` may contain, the orq-lite directory structure that provides per-role breakdowns, and three cross-cutting topics: wall-clock normalization, cost basis, and arm verification.

All field names below use the dot-path form from `telemetry.json`, e.g. `totals.input_tokens`.

---

## Claude Code stream (`--output-format stream-json`)

One JSON object per line. There is exactly one `type == "result"` record; it holds the authoritative totals for the run.

### Relevant records

| Filter | JSON path | `telemetry.json` field |
|---|---|---|
| `type == "system"`, `subtype == "init"` | `.cwd` | run context |
| `type == "system"`, `subtype == "init"` | `(.mcp_servers \| length)` | arm verification (see §Verifying) |
| `type == "system"`, `subtype == "init"` | `.tools`, `.permissionMode` | run context |
| `type == "assistant"` | `.message.content[] \| select(.type=="tool_use")` | tool counts, files read/written, subagent dispatches |
| `type == "result"` | `.usage.input_tokens` | `totals.input_tokens` |
| `type == "result"` | `.usage.output_tokens` | `totals.output_tokens` |
| `type == "result"` | `.usage.cache_read_input_tokens` | `totals.cache_read_tokens` |
| `type == "result"` | `.usage.cache_creation_input_tokens` | `totals.cache_write_tokens` |
| `type == "result"` | `.total_cost_usd` | `totals.cost_usd` |
| `type == "result"` | `.num_turns` | `totals.turns` |
| `type == "result"` | `.duration_ms / 1000` | `totals.wall_clock_seconds` |
| `type == "result"` | `.is_error`, `.stop_reason` | run context |
| `type == "rate_limit_event"` | count of such lines | `totals.rate_limit_events` |

`totals.reasoning_tokens` is not emitted by Claude Code; leave it `0`.

Set `cost_basis: "reported_by_provider"`.

### Recipe: extract totals from `stdout.log`

Returns the raw numbers before wall-clock normalization.

```sh
jq -s 'map(select(.type=="result")) | .[0] |
  {input: .usage.input_tokens, output: .usage.output_tokens,
   cache_read: .usage.cache_read_input_tokens,
   cache_write: .usage.cache_creation_input_tokens,
   cost_usd: .total_cost_usd, turns: .num_turns, duration_ms: .duration_ms}' stdout.log
```

---

## Codex stream

One JSON object per line. Three corrections are required when reading the `turn.completed` token fields; each is stated below with the consequence of skipping it.

### Relevant records

| Filter | JSON path | `telemetry.json` field |
|---|---|---|
| `type == "turn.completed"` | `.usage.input_tokens` | see Correction 1 |
| `type == "turn.completed"` | `.usage.cached_input_tokens` | see Correction 1 |
| `type == "turn.completed"` | `.usage.output_tokens` | see Correction 2 |
| `type == "turn.completed"` | `.usage.reasoning_output_tokens` | see Correction 2 |
| `type == "item.completed"`, `.item.type == "command_execution"` | `.item.command` (strip `/bin/zsh -lc "` wrapper) | bash activity |
| `type == "item.completed"`, `.item.type == "file_change"` | `.item.changes[].path` | files written |
| `type == "item.completed"`, `.item.type == "agent_message"` | count | `totals.turns` |

### Three required corrections

**Correction 1 — `input_tokens` is inclusive of `cached_input_tokens`.**

`.usage.input_tokens` counts all input including the portion served from the cache. Reporting it directly double-counts the cached input, which inflates the token count and therefore the cost for the Codex arm only, making cross-arm comparisons invalid.

Apply:

```
totals.input_tokens      = .usage.input_tokens - .usage.cached_input_tokens
totals.cache_read_tokens = .usage.cached_input_tokens
```

**Correction 2 — `reasoning_output_tokens` must be added into `output_tokens`.**

`.usage.output_tokens` does not include reasoning tokens. Reporting it directly under-counts the Codex arm's output, leading to a cost underestimate and an incomparable output count.

Apply:

```
totals.output_tokens    = .usage.output_tokens + .usage.reasoning_output_tokens
totals.reasoning_tokens = .usage.reasoning_output_tokens
```

**Correction 3 — Codex emits no cost field.**

There is no cost field anywhere in the Codex stream. Cost must be computed from the corrected token counts at a rate written into `cost_basis_note`. Skipping this step leaves `totals.cost_usd` at zero, causing the Codex arm to appear free.

```
cost_basis:      "computed_from_token_counts"
cost_basis_note: "<model> at $X.XX/1M input, $X.XX/1M output (retrieved <date>)"
```

`totals.cache_write_tokens` is not emitted by Codex; leave it `0`.

Never compare a Codex arm's computed cost against a Claude arm's provider-reported cost without documenting the basis difference in the report (see §Cost basis).

---

## opencode stream

One JSON object per line. **opencode does not emit a single terminal totals record. Token counts and cost accumulate across every `step_finish` event for the session.** Claude Code and Codex both deliver totals once; opencode requires summing across all `step_finish` events. Reading only the last `step_finish` produces a single-step count, not a session total.

### Relevant records

| Filter | JSON path | `telemetry.json` field (accumulate) |
|---|---|---|
| `type == "step_finish"` | `.part.tokens.input` | `totals.input_tokens` |
| `type == "step_finish"` | `.part.tokens.output` | included in `totals.output_tokens` (see note) |
| `type == "step_finish"` | `.part.tokens.reasoning` | `totals.reasoning_tokens`; also add to `totals.output_tokens` |
| `type == "step_finish"` | `.part.tokens.cache.read` | `totals.cache_read_tokens` |
| `type == "step_finish"` | `.part.tokens.cache.write` | `totals.cache_write_tokens` |
| `type == "step_finish"` | `.part.cost` | `totals.cost_usd` |
| `type == "step_finish"` | count of events | `totals.turns` |
| `type` in `{"tool","tool_use","part_updated","message_part_updated"}` when `.part.type == "tool"` | `.part.tool`, `.part.state.input`, `.part.state.status` | tool counts |

`totals.output_tokens` = sum of (`.part.tokens.output` + `.part.tokens.reasoning`) across all `step_finish` events.

### Recipe: accumulate totals from `stdout.log`

Returns summed values across the full session.

```sh
jq -s '[.[] | select(.type=="step_finish")] |
  {input:       (map(.part.tokens.input // 0) | add),
   output:      (map((.part.tokens.output // 0) + (.part.tokens.reasoning // 0)) | add),
   reasoning:   (map(.part.tokens.reasoning // 0) | add),
   cache_read:  (map(.part.tokens.cache.read // 0) | add),
   cache_write: (map(.part.tokens.cache.write // 0) | add),
   cost_usd:    (map(.part.cost // 0) | add),
   turns:       length}' stdout.log
```

### Tool event de-duplication

opencode re-emits `part_updated` events at each stage of a tool call. Count each unique call exactly once:

1. Collect events where the type is `tool`, `tool_use`, `part_updated`, or `message_part_updated` and `.part.type == "tool"`.
2. Skip any event where `.part.state.status` is set and not `"completed"`.
3. De-duplicate on the pair `(part.tool, part.state.input serialised to JSON, first 200 chars)`.

Set `cost_basis: "reported_by_provider"` (opencode reports `.part.cost` per step).

---

## orq-lite runs

Per-invocation artifacts live under:

```
.orquestalite/runs/<run_id>/agents/<activity>/<invocation>/
```

Each invocation directory contains:

| File | Contents |
|---|---|
| `meta.json` | `provider`, `agent`, `model`, `session_id`, `duration_s`, `exit_code` |
| `prompt.md` | Prompt sent to this invocation |
| `stdout.log` | Stream output; parser is selected by `meta.json.provider` |

`meta.json.provider` selects the parser: `"claude"` → Claude Code parser; `"codex"` → Codex parser; any other value → opencode parser.

### Invocation directory name

The directory name encodes role, cycle, attempt, and retry:

```
<role>.c<N>.a<N>[.r<N>]
```

Regex: `^([a-z_0-9]+)\.c(\d+)\.a(\d+)(?:\.r(\d+))?$`

| Capture group | Field | Use |
|---|---|---|
| 1 | role | `by_role[].role` |
| 2 | cycle | cycle counter (informational) |
| 3 | attempt | contributes to `totals.attempts` |
| 4 | retry | optional; records technical retries within an attempt |

`totals.attempts` counts invocations where the attempt index (group 3) is greater than 1; each such invocation represents a re-attempt issued by the orchestrator after an earlier failure.

`totals.agent_invocations` is the total count of all invocation directories processed, regardless of role, cycle, or attempt index.

### Filling `by_role[]`

Group all invocations by role (regex group 1). For each group:

| `by_role[]` field | Source |
|---|---|
| `role` | regex group 1 from the directory name |
| `provider` | `meta.json.provider` |
| `model` | `meta.json.model` |
| `invocations` | count of directories in this role group |
| `input_tokens` | sum of parsed `totals.input_tokens` across the group |
| `output_tokens` | sum of parsed `totals.output_tokens` across the group |
| `cache_read_tokens` | sum of parsed `cache_read` across the group |
| `cache_write_tokens` | sum of parsed `cache_write` across the group |
| `cost_usd` | sum of parsed `cost_usd` across the group |
| `duration_seconds` | sum of `meta.json.duration_s` across the group |

---

## Wall-clock net of rate limits

`totals.wall_clock_seconds` is raw elapsed time:

- **Claude Code:** `duration_ms / 1000` from the `type == "result"` record.
- **orq-lite runs:** sum of `meta.json.duration_s` across all invocation directories.

`totals.wall_clock_seconds_net_of_rate_limits` subtracts two categories of dead time:

1. **Provider incidents** — windows recorded in `manifest.environment.provider_incidents`. Each entry is a start/end timestamp; sum the durations that overlap the run window.

2. **Rate-limit events** — each `type == "rate_limit_event"` line in a Claude Code stream represents a pause imposed by the API. If the event carries a duration field, subtract it; otherwise subtract the span between the event timestamp and the next non-rate-limit event timestamp.

`totals.rate_limit_events` is the count of `type == "rate_limit_event"` lines in the log.

---

## Cost basis

`cost_basis` takes one of two values:

| Value | When to use |
|---|---|
| `"reported_by_provider"` | The provider emits a cost field in the stream (Claude Code: `.total_cost_usd`; opencode: sum of `.part.cost` across `step_finish` events). |
| `"computed_from_token_counts"` | The provider does not emit a cost field (Codex). Token counts are multiplied by a rate recorded in `cost_basis_note`. |

Never mix the two bases within a single comparison without noting the difference in the report. In round 4, the `gpt-sol` arm used a computed cost while its counterpart used a provider-reported cost at a different effective rate; the figure was incomparable until both arms were recomputed on the same basis.

When `cost_basis == "computed_from_token_counts"`, `cost_basis_note` must record the model name, the per-token rates used, and the retrieval date:

```
"cost_basis_note": "o3 at $2.00/1M input, $8.00/1M output, retrieved 2026-08-01"
```

---

## Verifying the arm is what you think it is

Before accepting telemetry, assert that the run matches the manifest's stated configuration.

**MCP arms** — assert that `n_mcp_servers` (from the `type == "system"`, `subtype == "init"` record: `len(.mcp_servers)`) differs between arms and matches the intent stated in the manifest. A zero count in an arm that was intended to use MCP means the server failed to start; the run is invalid and must not be included in the comparison.

**Model arms** — assert that `meta.json.model` in every invocation directory matches the model assignment in the manifest. A mismatch means the runtime fell back to a default; the arm is not the intended configuration.

**Fallback-capable runtimes** — some runtimes silently delegate to a different agent when the intended one is unavailable. Check whether the artifact was produced by the intended agent via `meta.json.agent`. If it was not, label the run `fallback_used: true` in the manifest. A fallback run is a data point but must not be mixed with clean runs in the same comparison.
