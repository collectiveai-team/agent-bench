# Rubric — M-relay

Dimension names are fixed by `references/evaluator-4-judge.md`. Anchors are written for
this case from scratch. Weights are adjusted from the L/S-family defaults; see the rationale
below.

**Reweighting rationale:**

The M-relay case spans three cold sessions, which shifts the discriminating power relative
to the single-session S-ledger case that covers the same final contract.

*Spec fidelity* rises from 25% to 30% (gaining 5%). The cross-leg consistency check is the
primary discriminator: a solver that recalled its decisions correctly will have a consistent
field-naming, ID-scheme, and error-body contract across all three sessions. Drift shows up as
continuity failures and — at a finer grain — as `rework_ratio` above zero. The rubric
dimension captures whether the final implementation is byte-exact against the full contract
across all three legs.

*Correctness and robustness* rises from 20% to 25% (gaining 5%). The atomicity and
error-body requirements are the second discriminator. A solver that re-derived conventions
in session 2 rather than recalling them may introduce subtle inconsistencies (e.g. a
different 404 body format, or a float-typed balance after session-2 rework).

*Concurrency and async correctness* drops from 10% to 3% (freeing 7%). The only async
surface is the standard FastAPI event loop and SQLAlchemy async sessions. This reduces to
"no blocking I/O in handlers," which is table-stakes and is not a meaningful discriminator
between arms in a continuity case. The dimension is retained at 3% so the judge still flags
egregious violations.

*Code quality and idiom* drops from 10% to 7% (freeing 3%). For a service of approximately
200 LOC of application code, style differences between arms are a weaker discriminator
relative to the continuity and correctness signals.

Net weights: 30 + 25 + 15 + 15 + 3 + 7 + 5 = **100%**. Arithmetic verified.

Score each dimension 1–5 (absolute protocol). Every score must cite at least one `file:line`
reference or command output; a score without evidence is discarded. Do not reward code
volume, comment density, or defensive boilerplate.

| Dimension | Weight | 1 | 3 | 5 |
|---|---|---|---|---|
| Spec fidelity | 30% | Endpoints or shapes deviate from the full contract; idempotency key logic absent or uses wrong status codes; OR `balance_minor` field is renamed or typed as float in any leg's code; OR error body format is inconsistent across legs (e.g. 404 uses `{"error": "..."}` in leg 2 but `{"detail": "..."}` in leg 1). | Contract mostly met across all three legs; minor drift in one area (e.g. transfer `created_at` is naive in leg-2 but aware in leg-1; or wrong status on replay 200 vs 201; or one idempotency case incorrect). | Every route, status code, body shape, and idempotency behaviour byte-exact across all three sessions; `balance_minor` is an integer throughout; both replay cases correct; error body `{"detail": "..."}` used identically by all endpoints; timestamps UTC-aware throughout. |
| Correctness and robustness | 25% | Reproducible data-loss path (double-debit, partial transfer without rollback); OR silent 500 on a domain error; OR leg-2 or leg-3 reworks leg-1 code in a way that breaks an existing test; OR `balance_minor` computed as a float at any point. | Correct happy paths across all legs; some sad paths unguarded (e.g. insufficient-funds check missing or outside the write transaction; transfer 404 body differs from account 404 body). | All failure modes handled per contract (400 missing header, 404 unknown account, 409 insufficient-funds + unchanged balances, 422 non-positive amount); transfer is atomic; no float arithmetic; continuity.md rows all pass. |
| Architecture and layering | 15% | Business logic in route handlers; no service layer; raw SQL in routes; OR significant code duplicated across session boundaries (same model or validation logic written twice). | Layering mostly respected; some business logic leaking into handlers; idempotency key check in the route rather than the service; minor session-boundary duplication. | Clean routes → services → repositories across all three sessions; idempotency key handling in the service; single-source constants; session-2 and session-3 additions extend rather than replace session-1 code. |
| Test quality | 15% | Happy-path only or no tests beyond the scaffold placeholder; OR leg-2 or leg-3 tests break leg-1 tests (ordering dependency, fixture state leak). | Criteria covered; some sad paths thin (missing 422 or 404 cases in solver's own tests); tests from later sessions reference test fixtures without proper isolation. | Independent, deterministic, self-contained (tmp-path SQLite per test); covers sad paths (400/404/409/422) and the integer-only invariant across all sessions; tests from session 1 pass unmodified in the session-3 repository; tests do not duplicate probe assertions. |
| Concurrency and async correctness | 3% | Blocking I/O in the event loop (synchronous SQLAlchemy calls, `time.sleep` in handlers). | Works under sequential load; no explicit blocking but event loop hygiene uncertain. | Async SQLAlchemy throughout all three sessions; no blocking I/O; transfer atomicity correct. |
| Code quality and idiom | 7% | Untyped, dead code, copy-paste across sessions, or ruff reports errors. | Typed and consistent with the conventions from session 1; ruff-clean; minor idiomatic gaps. | Idiomatic SQLAlchemy 2 / Pydantic v2 throughout all three sessions; `TZDateTime` or equivalent for timezone-safe persistence applied consistently; session-boundary code follows the same style as session-1 code; ruff-clean. |
| Docs and DX | 5% | README missing or wrong (missing quickstart, missing endpoint table, or wrong commands). | Quickstart works (`uv sync`, `uvicorn app.main:app`); endpoint table incomplete (covers some but not all six routes from all three sessions). | Accurate ops story: quickstart, full endpoint table covering all routes from all three sessions, the two gate commands. |
