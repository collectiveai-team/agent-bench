# Rubric — R-envelope

Dimension names are fixed by `references/evaluator-4-judge.md`. Anchors are
written for this case from scratch. Weights are adjusted from the R-family
defaults; see the rationale below.

**Reweighting rationale:**

*Spec fidelity* rises from 25% to 30% (gaining 5%). For a refactor case the
primary discriminator between arms is whether the solver found and migrated
every error path. Missing even one site fails the sweep completeness goal and
should dominate the score.

*Correctness and robustness* rises from 20% to 25% (gaining 5%). Envelope
correctness — all five members present, correct types, no member null, `status`
matching the wire code — is the second discriminator.

*Docs and DX* drops from 5% to 2% (losing 3%). No documentation is required
or even meaningful for this refactor; the dimension is retained at 2% so that
a solver who gratuitously removes the existing README still registers a small
penalty.

*Concurrency and async correctness* drops from 10% to 5% (losing 5%). The
exception handlers are registered once and are async coroutines, but the
refactor adds no new concurrency logic. Egregious failures (e.g. a handler
that calls a blocking I/O function) still register, but typical
implementations converge here.

*Code quality and idiom* drops from 10% to 8% (losing 2%). For a focused
refactor of approximately 30–50 LOC of new handler code, style differences
are a weak discriminator.

Net weights: 30 + 25 + 15 + 15 + 5 + 8 + 2 = **100%**. Arithmetic verified.

Score each dimension 1–5 (absolute protocol). Every score must cite at least
one `file:line` reference or command output; a score without evidence is
discarded. Do not reward code volume, comment density, or defensive
boilerplate.

| Dimension | Weight | 1 | 3 | 5 |
|---|---|---|---|---|
| Spec fidelity | 30% | One or more of the six error paths does not return `application/problem+json`; OR the Content-Type header is wrong on at least one path; OR a success response has been wrapped in the envelope. | All six error paths return problem+json but one or two member values are wrong (e.g. `status` is a string instead of an integer; `instance` is null or absent; `detail` contains the raw Python error dict instead of a string). | All six error paths return `application/problem+json` with all five members present and correctly typed; `status` equals the HTTP status code; `instance` is the request path; no success response is wrapped; existing error-shape assertions in the test suite are updated. |
| Correctness and robustness | 25% | `status` member does not match the HTTP status code on at least one path; OR `instance` is missing or null; OR a probe test fails for a path the solver claimed to have migrated. | All five required members present and non-null, but one member is subtly wrong (e.g. `title` varies across invocations of the same status code; `type` is an empty string or the literal `"about:blank"` with no documented rationale; `detail` is the string `"null"`). | All five members correct on every error path; `title` is stable across invocations of the same status code; `type` is a non-empty URI reference; `detail` is the original error message string (human-readable, not a raw Python data structure); `instance` starts with `/`. |
| Architecture and layering | 15% | Exception handling logic is copy-pasted into every route handler without a shared mechanism; no central handler is registered; logic is duplicated. | A custom `exception_handler` is registered for at least one error class; some paths still use the old `application/json` shape or the handler does not cover all three error classes (HTTPException, RequestValidationError, Exception). | Custom `exception_handler` registered for all three error classes (HTTPException, RequestValidationError, Exception); a shared formatting helper eliminates duplication; handler is placed in the app factory so it is active for all routes and all test clients. |
| Test quality | 15% | Existing tests that asserted the old `{"detail": "..."}` shape are still asserting the old shape (tests fail or are wrong); OR one or more success-path tests have been changed. | Error-shape assertions updated in the existing tests; but the assertions in the updated tests are loose (e.g. checking only status code, not Content-Type or body members). | All error-shape assertions updated to check Content-Type and at least `status` and `detail` from the new envelope; no success-path test changed; new test file passes without touching the two gate commands. |
| Concurrency and async correctness | 5% | Handler is defined as a sync function in an async application, causing blocking I/O in the event loop; OR handler is not registered at application startup (registered lazily inside a request, causing a race). | Handler is async but captures a mutable closure from the outer scope (e.g. a mutable list used for error accumulation). | Handler is a proper `async def` coroutine; no shared mutable state; registered once in the app factory before any request is served. |
| Code quality and idiom | 8% | Untyped handler signature; hardcoded status-phrase strings as a long if/elif ladder; HTTP status phrase derived by hand with no stdlib support; ruff reports errors. | Typed but uses a hardcoded dict of status phrases; or reads `phrase` from an external string that duplicates what `http.HTTPStatus` already provides; ruff-clean. | Handler signature is fully typed; HTTP status phrase obtained from `http.HTTPStatus` (stdlib) or an equivalent authoritative source; helper function extracted and reused across all handlers; ruff-clean. |
| Docs and DX | 2% | Existing README removed or its content meaningfully degraded as a side effect of the refactor. | README unchanged. | README unchanged and the commit description or an inline comment explains the migration approach (e.g. which exception classes are handled and why). |
