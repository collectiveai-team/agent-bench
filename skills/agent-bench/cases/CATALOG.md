# Case catalog

This file is the contract that Tasks 10-17 implement against. Cases listed here do not exist yet; each task creates one. Do not add a row for a case until its `case.md`, `spec/`, `scaffold/`, `acceptance.md`, `rubric.md`, and `probes/` are all committed.

## Cases

| ID | Family | Base | Expected duration | Expected cost | What it separates | What it does not measure |
| --- | --- | --- | --- | --- | --- | --- |
| `L-taskflow` | Long greenfield | Ported from prior benchmark | 2–6 h | $15–60 | End-to-end capability, governance, convergence | Codebase navigation; defect detection; cross-session continuity |
| `L-hookrelay` | Long greenfield | Ported from prior benchmark | 2–6 h | $15–60 | A second independent spec, so conclusions do not rest on one case | Codebase navigation; defect detection; cross-session continuity |
| `S-ledger` | Short greenfield | New | 15–45 min | $1–4 | Idempotency keys, boundary math on balances, structured error bodies; cheap enough for N ≥ 5 | Codebase navigation; defect detection; cross-session continuity |
| `S-ingest` | Short greenfield | New | 15–45 min | $1–4 | Schema-validating ingest CLI with bad-row quarantine; non-API shape, so "short" is not always the same kind of task | Codebase navigation; defect detection; cross-session continuity |
| `B-sabotage` | Bug hunt | Frozen good `L-taskflow` implementation (`_base-taskflow`) plus defect patches | 10–30 min | $1–3 | Detection capability rather than authoring capability | Authoring; architecture; greenfield design |
| `R-envelope` | Multi-file refactor | Same frozen base (`_base-taskflow`) | 30–90 min | $2–8 | Complete sweep over a sealed site list; where subagent strategies should separate from single-session ones | Greenfield design; defect detection; cross-session continuity |
| `M-relay` | Multi-session | `S-ledger` split into 3 legs with cold context between legs | 1–2 h | $4–12 | Cross-session continuity; the only design where a memory MCP can produce signal | Greenfield scale; codebase navigation |

## Shared bases

`_base-taskflow` — a frozen, known-good implementation of `L-taskflow`. It is not a runnable case; it is a stable starting point that families B and R require. `B-sabotage` applies seeded defect patches on top of it. `R-envelope` treats it as the sealed codebase to refactor. See `references/adding-a-case.md § Validating probes without shipping a solution` for why this is the only committed reference implementation in the repository.

## Choosing a case

Use this section to match a hypothesis to the right case before framing a comparison. The framing step in `SKILL.md` requires that the case's "What this case does NOT measure" section does not cover the hypothesis; check here first.

**You want to compare overall coding capability end to end.** Use `L-taskflow` or `L-hookrelay`. These are the longest cases and the most sensitive to differences in planning, architecture, and convergence. Use both when you want conclusions that do not rest on a single spec.

**Your hypothesis is about a specific short-form behavior** (idempotency handling, boundary math, error body structure). Use `S-ledger`. It is cheap enough to run at N ≥ 5 in a single session, which makes the decision rule from `references/scoring.md` more reliable.

**You want to test ingest-style CLI work** rather than an HTTP service. Use `S-ingest`. It shares the short-form cost profile of `S-ledger` but exercises a different task shape.

**Your hypothesis is about defect detection**, not code authoring. Use `B-sabotage`. This is the only family that scores a findings report rather than an implementation; running any other case and judging it on defect detection would conflate authoring quality with detection quality.

**Your hypothesis is about refactoring discipline** — whether an agent completes a change across all required sites without scope creep or regressions. Use `R-envelope`. This is the only family that measures site coverage over a sealed list.

**Your hypothesis involves memory, context retention, or continuity across sessions.** Use `M-relay`. The rule is absolute: a memory or context-retention hypothesis requires `M-relay`; no single-session case can answer it. `M-relay` is the only design where a memory MCP or long-context strategy can produce signal that is attributable to continuity rather than authoring quality.

**Hypotheses that no current case covers.** If the "What this case does NOT measure" section of every case covers your hypothesis, do not run a comparison and declare a winner. Either design a new case or narrow the hypothesis to something an existing case can measure. See `references/adding-a-case.md` for the authoring workflow.
