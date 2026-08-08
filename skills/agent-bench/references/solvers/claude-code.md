# claude-code solver notes

> These notes may go stale. The protocol depends only on `manifest.json` recording the exact command actually used.

## Headless launch

Supply `--output-format stream-json` so the output is machine-readable. Pass the prompt non-interactively (check `claude --help` for the current flag; confirm the flag resolves before launch rather than discovering mid-run that output is interactive). Redirect all output to a log path recorded in `telemetry.source_logs`.

```sh
nohup caffeinate -i claude --output-format stream-json \
  <prompt-flag> "$(cat prompt.md)" \
  > /tmp/<run>-launch.log 2>&1 < /dev/null &
disown
```

See `references/run-protocol.md` for the full pre-flight checklist.

## Where the log lands

Wherever `telemetry.source_logs` points. The file contains one JSON object per line.

## Stream format

See the **Claude Code stream (`--output-format stream-json`)** section of `references/telemetry.md` for the full record table, the token field paths, the extraction recipe, and the arm-verification check on `n_mcp_servers`.

Key: there is exactly one `"type": "result"` record per run. Read totals from that record only; do not accumulate across multiple records. `totals.reasoning_tokens` is not emitted by Claude Code; leave it `0`.

## Pinning the configuration

Record in `manifest.solver`:

| Field | What to capture |
|---|---|
| `launch_command` | Exact command verbatim, including all flags |
| `binaries[].name` | `claude` |
| `binaries[].version` | Output of `claude --version` |
| `binaries[].sha256` | sha256 of the claude binary |
| `model_assignments` | The model id as it will appear in the `"result"` record |

For MCP arms: list every MCP server in `manifest.solver.mcp_servers` and assert that `n_mcp_servers` (from the `"system"` / `"init"` record: `length(.mcp_servers)`) differs between arms and matches the manifest intent. A zero count in an arm intended to use MCP means the server failed to start; the run is invalid and must not be included in the comparison.

Skills and plugins present in the environment change behaviour — they alter the tool list, available context, and the actions the agent can take. They are either part of the held-constant set or they *are* the independent variable. Either way, they must be recorded: list them in `manifest.solver.config_files` or `manifest.solver.mcp_servers` and set `differs_between_arms` accordingly. A run with unexpected skills active is not a clean arm.

## Known traps

- Skills and plugins active in the shell environment at launch time change the tool list and available context. Failing to lock this down means two arms differ on a variable you did not intend to vary, and the comparison is invalid.
- Permission mode affects what the agent can do (file writes, command execution, network access). It must be identical across all arms; a stricter mode in one arm silently limits the actions available and produces an incomparable result.
