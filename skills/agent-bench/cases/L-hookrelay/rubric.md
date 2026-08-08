# Rubric — L-hookrelay

Dimension names and weights are fixed by `references/evaluator-4-judge.md`. Anchors are adapted from `orquesta-lite/benchmark/round2/evaluation.md` §3.2, which states "Same as round 1 with domain nouns updated" and does not reprint the anchor table. The anchors below are the `L-taskflow` anchors reworked to hookrelay's surface: SSE instead of WebSocket, delivery dispatcher instead of Prefect worker, HMAC signing as an additional correctness dimension.

Score each dimension 1–5 (absolute protocol). Every score must cite at least one `file:line` reference or command output; a score without evidence is discarded. Do not reward code volume, comment density, or defensive boilerplate.

| Dimension | Weight | 1 | 3 | 5 |
|---|---|---|---|---|
| Spec fidelity | 25% | endpoints/shapes deviate from `features.md` | contract met, minor drift in edge bodies or signature header format | every shape, status code, header, and SSE frame byte-exact, edge cases (409, dead-letter, inactive exclusion) included |
| Correctness and robustness | 20% | reproducible crash, data loss, or signing error | correct happy paths; some sad paths unguarded | failure modes handled and persisted per contract (retries, dead letters, disconnects, invalid input, shutdown with no stuck `sending` rows) |
| Architecture and layering | 15% | logic in handlers, duplicated constants, tangled imports | layering mostly respected, small leaks | clean routes→service→repo, dispatcher/bus properly abstracted, delivery-client seam (`http.delivery_client_factory`) preserved, single-source constants |
| Test quality | 15% | happy-path only, order-dependent, sleeps | criteria covered, some sad paths thin | independent, deterministic, sad-path rich (retries, dead letters, inactive subscriptions, disconnects, shutdown), meaningful assertions (not snapshot noise) |
| Concurrency and async correctness | 10% | blocking I/O in loop, leaked SSE subscriptions, unhandled `CancelledError` | works but fragile (unbounded queues, missing cancellation on SSE or dispatcher) | bounded fan-out, cancellation-safe lifespan/SSE/dispatcher shutdown, no `sending` rows after teardown, no event-loop blocking |
| Code quality and idiom | 10% | untyped, dead code, copy-paste | typed and consistent with `CONVENTIONS.md` | idiomatic SQLAlchemy 2/Pydantic v2/asyncio throughout, minimal and clear |
| Docs and DX | 5% | README missing/wrong | quickstart works | accurate ops story including HMAC signature verification snippet, full endpoint table, and both gate commands |
