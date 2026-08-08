# orq-lite solver notes

> These notes may go stale. The protocol depends only on `manifest.json` recording the exact command actually used.

## Headless launch

Flags go immediately after the flow reference, before `key=value` arguments. Reversing this order silently drops the flag.

```sh
nohup caffeinate -i .orquestalite/bin/orq-lite flow run <pack>/<flow>@<v> \
  --policy=.orquestalite/<policy>.json \
  features_path=features.md \
  > /tmp/<run>-launch.log 2>&1 < /dev/null &
disown
```

Verify `orq-lite doctor` is green before running this command. See `references/run-protocol.md` for the full pre-flight checklist.

## Where the log lands

Running log: `.orquestalite/run.log`

Per-invocation artifacts:

```
.orquestalite/runs/<run_id>/agents/<activity>/<invocation>/
  meta.json     provider, agent, model, session_id, duration_s, exit_code
  prompt.md     prompt sent to this invocation
  stdout.log    stream output; parser selected by meta.json.provider
```

## Stream format

Per-invocation. `meta.json.provider` selects the parser:

- `"claude"` → Claude Code parser
- `"codex"` → Codex parser
- any other value → opencode parser

See the **orq-lite runs** section of `references/telemetry.md` for the invocation directory name encoding, how to fill `by_role[]`, and how to aggregate token counts and cost across roles.

## Pinning the configuration

Before the round begins, copy the built binary into a stable location. Record it in `manifest.solver.binaries`:

```
name:    orq-lite
version: <output of orq-lite --version>
sha256:  <sha256sum of the binary>
```

Never rebuild mid-round. A rebuild changes the binary under test; runs before and after are not comparable.

Record the policy file path in `manifest.solver.config_files` with `differs_between_arms` set to reflect whether arms vary on the policy. Record the exact launch command verbatim in `manifest.solver.launch_command`.

## Known traps

- `flow run` does not accept `--log-format`; passing it causes the command to exit immediately with an unrecognised flag error.
- A policy file placed inside a pack directory breaks pack validation: orq-lite reports `pack: unlisted file` and the run aborts before any work is done. Keep policy files outside all pack directories.
- Without an explicit `--policy` flag, an older pack silently falls back to the engine default budget; the run proceeds but the budget in `manifest.json` does not govern execution, so budget-controlled comparisons are invalid.
- `orq-lite doctor` must be green before launch; a failing doctor check indicates a missing dependency or misconfigured environment that will cause a mid-run abort.
