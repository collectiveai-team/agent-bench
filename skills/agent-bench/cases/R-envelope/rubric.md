# Rubric — R-envelope

Dimension names are fixed by `references/evaluator-4-judge.md`. Anchors are
written for this case from scratch. Weights are adjusted from the R-family
defaults; see the rationale below.

**Reweighting rationale:**

*Spec fidelity* rises from 25% to 30% (gaining 5%). The two-half structure
means the primary discriminator is whether the solver found and migrated every
envelope site AND threaded context explicitly through every sealed propagation
signature. Missing even one half fails the sweep completeness goal and should
dominate the score.

*Correctness and robustness* stays at 25%. Envelope correctness (all five
members present, correct types, `instance` starts with `/`) and propagation
correctness (request_id in every HTTP-originated event) are the second
discriminator.

*Architecture and layering* rises from 15% to 18% (gaining 3%). The
propagation half specifically exercises whether the solver chose explicit
parameter threading over ambient state (contextvars, globals). The layering
dimension captures this.

*Docs and DX* drops from 5% to 2% (losing 3%). No documentation is required
or even meaningful for this refactor; the dimension is retained at 2% so that
a solver who gratuitously removes the existing README still registers a small
penalty.

*Concurrency and async correctness* stays at 5%. The exception handlers are
registered once and are async coroutines, but the refactor adds no new
concurrency logic. Egregious failures (e.g. a handler that calls a blocking
I/O function, or a ContextVar used to work around the explicit-threading
constraint) still register.

*Code quality and idiom* drops from 10% to 7% (losing 3%). For a focused
refactor of approximately 50–80 LOC of new handler and context code, style
differences are a weak discriminator.

*Test quality* stays at 15%. Both halves require test updates: the envelope
half requires updating two error-shape assertions; the propagation half does
not require new tests beyond what the probes cover (existing tests do not
check `request_id`).

Net weights: 30 + 25 + 18 + 15 + 5 + 7 + 2 = **102%** — reduce test quality
to 13%: 30 + 25 + 18 + 13 + 5 + 7 + 2 = **100%**. Arithmetic verified.

Score each dimension 1–5 (absolute protocol). Every score must cite at least
one `file:line` reference or command output; a score without evidence is
discarded. Do not reward code volume, comment density, or defensive
boilerplate.

| Dimension | Weight | 1 | 3 | 5 |
|---|---|---|---|---|
| Spec fidelity | 30% | One or more of the six envelope error paths does not return `application/problem+json`; OR the propagation half is entirely missing; OR the Content-Type header is wrong on at least one error path; OR a success response has been wrapped in the envelope. | All six envelope error paths return problem+json but one or two member values are wrong (e.g. `status` is a string; `instance` is null or absent; `detail` contains a raw Python dict). The propagation half is partially implemented (some but not all propagation sealed files touched). | All six envelope error paths return `application/problem+json` with all five members present and correctly typed; `status` equals the HTTP status code; `instance` starts with `/`; no success response is wrapped. All three propagation sealed files touched; `request_id` appears in the `job.created` event. Existing error-shape assertions in the test suite are updated. |
| Correctness and robustness | 25% | `status` member does not match the HTTP status code on at least one path; OR `instance` is missing, null, or does not start with `/`; OR `request_id` is missing from the `job.created` event; OR a probe test fails. | All five required envelope members present and non-null, but one is subtly wrong (e.g. `title` varies across invocations of the same status code; `detail` is the string `"null"`). Propagation implemented but `request_id` is derived from ambient state rather than the explicit parameter. | All five envelope members correct on every error path; `title` stable per status code; `detail` is human-readable; `instance` starts with `/`. `request_id` in the `job.created` event matches a UUID generated and passed explicitly from the route handler. |
| Architecture and layering | 18% | Envelope logic is copy-pasted into every route handler with no shared mechanism. Propagation uses `contextvars.ContextVar` or a module-level global instead of explicit parameter threading. | A shared `exception_handler` registered for at least one error class; some error paths still return `application/json`. Propagation uses explicit parameters in the service layer but not in the repository layer (or vice versa). | `exception_handler` registered for all three error classes (HTTPException, RequestValidationError, Exception); shared formatting helper; handler in the app factory. `RequestContext` passed as an explicit parameter through the full stack: route → service → repository → `create_job_event`. No ambient state used. |
| Test quality | 13% | Existing tests that asserted the old `{"detail": "..."}` shape are still asserting the old shape (tests fail or are wrong); OR one or more success-path tests have been changed. | Error-shape assertions updated in the existing tests; but assertions are loose (e.g. checking only status code, not Content-Type or body members). | All error-shape assertions updated to check Content-Type and at least `status` and `detail` from the new envelope; no success-path test changed; gate commands still pass. |
| Concurrency and async correctness | 5% | Handler is a sync function in an async application, causing blocking I/O; OR a `ContextVar` is used (violating the explicit-threading constraint and making context invisible to async task boundaries). | Handler is async but captures a mutable closure from the outer scope. | Handler is a proper `async def` coroutine; no shared mutable state; registered once in the app factory; `RequestContext` is frozen (immutable). |
| Code quality and idiom | 7% | Untyped handler signature; hardcoded status-phrase strings as a long if/elif ladder; `RequestContext` is a mutable plain dict; ruff reports errors. | Typed but uses a hardcoded dict of status phrases; or `RequestContext` is a regular (mutable) class; ruff-clean. | Handler signature is fully typed; status phrase from `http.HTTPStatus` or an equivalent source; `RequestContext` is a frozen dataclass; helper function extracted and reused across all handlers; ruff-clean. |
| Docs and DX | 2% | Existing README removed or its content meaningfully degraded as a side effect of the refactor. | README unchanged. | README unchanged and the commit description or an inline comment explains the migration approach (which exception classes are handled and why; that ctx is explicit rather than ambient). |
