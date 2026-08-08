# codex solver notes

> These notes may go stale. The protocol depends only on `manifest.json` recording the exact command actually used.

## Headless launch

Use the `exec` subcommand (`codex exec`, alias `e`) to run Codex non-interactively. The prompt is a positional argument. Verify `codex exec --help` before launching — subcommand behaviour can change across versions. Redirect all output to a log path recorded in `telemetry.source_logs`.

```sh
nohup caffeinate -i codex exec "$(cat prompt.md)" \
  > /tmp/<run>-launch.log 2>&1 < /dev/null &
disown
```

See `references/run-protocol.md` for the full pre-flight checklist.

## Where the log lands

Wherever `telemetry.source_logs` points. The file contains one JSON object per line.

## Stream format

See the **Codex stream** section of `references/telemetry.md` for the full record table and the three required corrections.

Key: Codex emits no cost field anywhere in the stream. `cost_basis` must be set to `"computed_from_token_counts"` and `cost_basis_note` must record the model name, the per-token rates used, and the retrieval date.

## Pinning the configuration

Record in `manifest.solver`:

| Field | What to capture |
|---|---|
| `launch_command` | Exact command verbatim |
| `binaries[].name` | `codex` |
| `binaries[].version` | Output of `codex --version` |
| `binaries[].sha256` | sha256 of the binary |
| `model_assignments` | The model id passed to the invocation |
| `config_files` | Provider credential files or `~/.codex/config.toml` overrides in effect, with sha256 and `differs_between_arms` |
| `mcp_servers` | Any MCP servers active during the run |

## Known traps

- (Correction 3) No cost field is emitted anywhere in the Codex stream. `totals.cost_usd` must be computed from corrected token counts; leaving it at zero makes the Codex arm appear free and cross-arm comparisons invalid. Set `cost_basis: "computed_from_token_counts"` and fill `cost_basis_note`. See Correction 3 in `references/telemetry.md`.
- (Correction 1) `.usage.input_tokens` is inclusive of `.usage.cached_input_tokens`. Reporting it directly double-counts the cached portion and inflates the input count for the Codex arm only, making cost comparisons invalid. Apply Correction 1 from `references/telemetry.md`.
- (Correction 2) `.usage.output_tokens` does not include reasoning tokens. Add `.usage.reasoning_output_tokens` before filling `totals.output_tokens`. Apply Correction 2 from `references/telemetry.md`.
