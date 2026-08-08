# Rubric — L-taskflow

Dimension names and weights are fixed by `references/evaluator-4-judge.md`. Anchors are ported verbatim from `orquesta-lite/benchmark/evaluation.md` §3.2 (the prior benchmark round that produced this case).

Score each dimension 1–5 (absolute protocol). Every score must cite at least one `file:line` reference or command output; a score without evidence is discarded. Do not reward code volume, comment density, or defensive boilerplate.

| Dimension | Weight | 1 | 3 | 5 |
|---|---|---|---|---|
| Spec fidelity | 25% | endpoints/shapes deviate from `features.md` | contract met, minor drift in edge bodies | every shape, code, and event byte-exact, edge cases included |
| Correctness and robustness | 20% | reproducible crash or data loss path | correct happy paths; some sad paths unguarded | failure modes handled and persisted per contract (failed jobs, disconnects, invalid input) |
| Architecture and layering | 15% | logic in handlers, duplicated constants, tangled imports | layering mostly respected, small leaks | clean routes→service→repo, dispatcher/bus properly abstracted, single-source constants |
| Test quality | 15% | happy-path only, order-dependent, sleeps | criteria covered, some sad paths thin | independent, deterministic, sad-path rich, meaningful assertions (not snapshot noise) |
| Concurrency and async correctness | 10% | blocking I/O in loop, leaked tasks/subscriptions, races | works but fragile (unbounded queues, missing cancellation) | bounded fan-out, cancellation-safe lifespan/WS cleanup, no event-loop blocking |
| Code quality and idiom | 10% | untyped, dead code, copy-paste | typed and consistent with `CONVENTIONS.md` | idiomatic SQLAlchemy 2/Pydantic v2/Prefect 3 throughout, minimal and clear |
| Docs and DX | 5% | README missing/wrong | quickstart works | accurate ops story incl. prefect worker mode and WS example |
