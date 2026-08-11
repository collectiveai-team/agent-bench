# agent-bench

A benchmark repository for comparing coding-agent configurations. One skill drives the protocol, a catalog of cases supplies the work, and no executable harness is maintained in this repository.

## Install

```sh
npx skills add collectiveai-team/agent-bench
```

The CLI clones the repository and copies `skills/agent-bench/` — including the full `cases/` tree — into the skills directory for your harness. Where that goes depends on context:

- **Run from inside a project directory:** installs to `.agents/skills/agent-bench/` in that project and creates a symlink at `.claude/skills/agent-bench`.
- **Run from outside any project (global install):** installs to `~/.agents/skills/agent-bench/` and symlinks into `~/.claude/skills/agent-bench`.

In both cases `SKILL.md`, `references/`, `templates/`, and `cases/` (all seven cases plus `_base-taskflow`) are present at the installed path.

### Install caveats

`npx skills add` was verified against `collectiveai-team/agent-bench` on 2026-08-10, run from inside a project directory. The complete `cases/` directory traveled with the install; no selective-copy behaviour was observed. All eight case directories (`_base-taskflow`, `B-sabotage`, `L-hookrelay`, `L-taskflow`, `M-relay`, `R-envelope`, `S-ingest`, `S-ledger`) were present at the installed path alongside `SKILL.md`, `references/` and `templates/`.

Only the project-local install path was exercised. The global path is documented from the CLI's behaviour with other skills on the same machine, not from a run against this repository.

If you need the skill accessible without running `npx skills add` — for example, in a CI environment — clone the repository and point `$AGENT_BENCH_HOME` at it:

```sh
git clone git@github.com:collectiveai-team/agent-bench.git ~/agent-bench
export AGENT_BENCH_HOME=~/agent-bench
```

The run ledger resolves `$AGENT_BENCH_HOME` before falling back to local discovery (see `## Ledger location` below).

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
