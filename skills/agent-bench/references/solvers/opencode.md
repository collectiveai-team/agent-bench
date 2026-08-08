# opencode solver notes

> These notes may go stale. The protocol depends only on `manifest.json` recording the exact command actually used.

## Headless launch

Use `opencode run` with `--format json` to get machine-readable output. Without `--format json` the stream is formatted for human display and the JSON paths in `references/telemetry.md` will not match. The message is positional. Verify `opencode run --help` before launching — versions drift. Redirect all output to a log path recorded in `telemetry.source_logs`.

```sh
nohup caffeinate -i opencode run --format json "$(cat prompt.md)" \
  > /tmp/<run>-launch.log 2>&1 < /dev/null &
disown
```

See `references/run-protocol.md` for the full pre-flight checklist.

## Where the log lands

Wherever `telemetry.source_logs` points. The file contains one JSON object per line.

## Stream format

See the **opencode stream** section of `references/telemetry.md` for the full record table, the tool de-duplication procedure, and the extraction recipe.

Key: opencode does not emit a single terminal totals record. Token counts and cost **accumulate across all `step_finish` events** for the session. Reading only the last `step_finish` gives a single-step count, not a session total.

## Pinning the configuration

Before the run, confirm the provider and model id actually resolve:

```sh
opencode models
```

A model id that does not appear in this output is a pre-launch blocker. Do not launch and discover mid-run that the model was unavailable; that wastes the full wall-clock budget and produces no valid telemetry.

Record in `manifest.solver`:

| Field | What to capture |
|---|---|
| `launch_command` | Exact command verbatim |
| `binaries[].name` | `opencode` |
| `binaries[].version` | Output of `opencode --version` |
| `binaries[].sha256` | sha256 of the binary |
| `model_assignments` | The provider/model id string as it appears in `opencode models` output |
| `config_files` | Provider credential files or opencode config files in effect, with sha256 and `differs_between_arms` |
| `mcp_servers` | Any MCP servers active during the run |

## Known traps

- Tool events are re-emitted as `part_updated` events at each stage of a tool call. Counting all events over-reports tool usage; de-duplicate on `(part.tool, serialised input)` and keep only events where `part.state.status == "completed"`. See the **Tool event de-duplication** subsection of `references/telemetry.md`.
- Quota exhaustion pauses a run for long periods without aborting it; wall-clock grows silently while no progress is made. Record the pause window in `manifest.environment.provider_incidents` and subtract it from `totals.wall_clock_seconds_net_of_rate_limits`.
