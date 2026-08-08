# _base-taskflow

## Identity

`_base-taskflow@1`

## Provenance

| Field | Value |
|---|---|
| Source directory | `/Users/lionelchamorro/Projects/personal/taskflow-r4-gpt-sol` |
| Scaffold commit (branch `bench-r4`) | `9edeaa6` |
| Copy date | 2026-08-08 |
| Tree content hash | `b1108581aeda4eccbf6960d757b99be0248c8ee6c390e6bae78d47013e9b29f4` |

The round-4 benchmark artifact lived in an **uncommitted working tree**. Branch `bench-r4` in the source repository points at scaffold commit `9edeaa6`; all of `app/` was delivered as untracked files and was never staged or committed. This copy — the tree stored here under `tree/` — is what pins that artifact. The content hash above is the authoritative fingerprint.

Hash command:

```bash
cd skills/agent-bench/cases/_base-taskflow/tree && \
  find . -type f -not -path './.venv/*' | sort | xargs shasum -a 256 | shasum -a 256
```

## Known deviations

These are deviations from the `L-taskflow` specification that exist in the base as delivered. They are documented here so that evaluators of `B-sabotage` and `R-envelope` runs can distinguish pre-existing deviations from seeded defects (B-family) or refactoring errors (R-family). A hunter who reports a deviation from this list should be neither credited with finding a seeded defect nor penalised as a false positive.

**1. Module-level `_event_bus` singleton (design deviation, no test failure)**

`app/events.py` exports a module-level `_event_bus = EventBus()` instance and `get_event_bus()` returns it. The specification calls for the event bus to be scoped to `app.state` (created fresh per application instance in the lifespan handler). The current implementation means all application instances in the same process share a single bus. `app/main.py` does assign `application.state.bus = get_event_bus()` — the reference is stored on state, but the underlying object is module-global. In testing the deviation is harmless because each test creates its own `TestClient` with a fresh in-memory DB and the bus queue drains between tests. In a production deployment with multiple workers it would cause cross-worker event bleed.

## Verification

### Suite gate (run against the stripped tree with its own `.venv`)

```bash
cd /tmp/agb-base-check
./.venv/bin/python -m ruff check .
./.venv/bin/python -m pytest -q
```

Expected output (last two significant lines):
```
All checks passed!
44 passed, 1 warning in N.NNs
```

Actual output recorded on 2026-08-08:
```
All checks passed!
44 passed, 1 warning in 8.96s
```

### Probe gate (L-taskflow probe, 14/14)

```bash
cp skills/agent-bench/cases/L-taskflow/probes/test_probe.py /tmp/agb-base-check/tests/
cd /tmp/agb-base-check && ./.venv/bin/python -m pytest tests/test_probe.py -q
```

Expected output:
```
14 passed, 1 warning in N.NNs
```

Actual output recorded on 2026-08-08:
```
14 passed, 1 warning in 9.41s
```

## What was stripped

The following were removed from the raw export before the tree was committed. The rsync that produced the export already excluded `.git`, `.orquestalite`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, and `.venv`. The explicit `rm` pass then removed:

| Path | Reason |
|---|---|
| `.orquestalite/` | Orquesta-lite run state; not part of the application |
| `.claude/` | Solver session artefacts |
| `.superpowers/` | Solver session artefacts |
| `docs/` | Solver-generated documentation |
| `prompts/` | Solver prompt scaffolding |
| `schemas/` | Solver schema scaffolding |
| `flows.json` | Orquesta-lite flow registry |
| `team.json` | Solver team configuration |
| `skills-lock.json` | Orquesta-lite lock file |
| `features.md` | Original build specification — would hand a bug hunter the acceptance criteria |
| `CONVENTIONS.md` | Original coding conventions — same exposure risk |

The `.venv` is excluded from the committed tree. Verification was run against a throwaway `/tmp/agb-base-check` copy that included a `.venv` copied from the source repository; the committed `tree/` directory contains no virtualenv.

## Staleness

If the base is regenerated from a different source or with different stripping, bump the version to `_base-taskflow@2`. A version bump invalidates cross-run comparability between `B-sabotage` and `R-envelope` runs from before and after the boundary. Tasks 15 and 16 must both cite the same base version; if they diverge, their scores are not comparable.

## Answer-key exposure

> This tree is a complete working implementation of `L-taskflow`'s specification, and this repository is public. Keeping it here is a deliberate trade: families B and R need a realistic codebase, and building one from nothing would cost more than the exposure does. The consequence is recorded in `cases/L-taskflow/case.md` under "Validity threat: a public reference implementation exists". Do not resolve this by deleting the base; resolve it, if it ever matters, by moving B and R onto a codebase that corresponds to no case in the catalog.
