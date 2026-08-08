# agent-bench

A benchmark repository for comparing coding-agent configurations. One skill drives the protocol, a catalog of cases supplies the work, and no executable harness is maintained in this repository.

## Install

```sh
npx skills add collectiveai-team/agent-bench
```

This copies `skills/agent-bench/` into `~/.agents/skills/` and symlinks it into each harness's skills directory.

## Use

Invoke the `agent-bench` skill inside your harness and name the two arms to compare. The skill runs both arms against the same case and scores the results.

Example: *"Compare orq-lite `factory_governed` with `fast=true` against `fast=false` on `S-ledger`, N=5."*

## What is in here

| Path | Contents |
|---|---|
| `skills/agent-bench/` | The protocol and the case catalog |
| `runs/` | Committed evidence, one directory per run |
| `docs/superpowers/` | Design spec and implementation plan |

## Ledger location

Runs are written to the first location that resolves:

1. `$AGENT_BENCH_HOME` if set
2. The current repository, if it is an agent-bench checkout
3. `./bench-runs/` — **warning: results written here are not recorded to the catalog**

## Design

[docs/superpowers/specs/2026-08-07-agent-bench-design.md](docs/superpowers/specs/2026-08-07-agent-bench-design.md)
