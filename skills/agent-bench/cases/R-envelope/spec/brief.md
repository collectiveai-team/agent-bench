# R-envelope — task brief

You are working in a copy of the `_base-taskflow@1` service: a FastAPI + SQLite
job-execution service with a WebSocket event stream and a Prefect worker. The
suite ships 44 passing tests. Both gates must remain green when you are done.

## Your task

This task has two halves. Both are required. Neither may be skipped.

---

## Half 1 — RFC 7807 error envelope

Migrate every error response the service can produce to the RFC 7807
Problem Details for HTTP APIs format, without changing any success response
and without breaking the existing test suite.

### Required envelope shape

Every error response must:

1. Set the HTTP `Content-Type` header to `application/problem+json`.
2. Return a JSON object body containing exactly these five members (additional
   members are permitted but not required):

| Member | Type | Constraint |
|---|---|---|
| `type` | string | A non-empty URI reference identifying the problem type. |
| `title` | string | A non-empty human-readable summary of the problem type. The same `type` URI must always have the same `title`. |
| `status` | integer | The HTTP status code of this response. Must equal the HTTP status code on the wire. |
| `detail` | string | A non-empty human-readable explanation specific to this occurrence of the problem. |
| `instance` | string | A non-empty URI reference identifying this specific occurrence. Must be the absolute path of the request (starts with `/`). |

No member may be `null`. All five must be present.

### Error paths you must cover

The service has the following error-producing paths; all must be migrated:

1. **404 — job not found** when `GET /jobs/{job_id}` is called with an unknown id.
2. **404 — job not found** when `DELETE /jobs/{job_id}` is called with an unknown id.
3. **409 — job is running** when `DELETE /jobs/{job_id}` is called on a job
   whose status is `running`.
4. **422 — application-level** when `GET /jobs` is called with an invalid
   `status`, `limit`, or `offset` query parameter (this path goes through
   `InvalidJobListQueryError` in the service layer).
5. **422 — framework-level** when `POST /jobs` is called with a request body
   that fails Pydantic validation (wrong `type` value or wrong `payload` type).
   FastAPI raises `RequestValidationError` before your handler is called; you
   must override this handler.
6. **500 — unhandled exception** when any route handler raises an exception
   that is not an `HTTPException` or `RequestValidationError`. The response
   must use the same problem+json envelope.

### Constraints

- Every error response must use `application/problem+json`. No error path may
  return `application/json`.
- Every success response (2xx) must be unchanged: the same body shape, the
  same HTTP status code, and `application/json` as the Content-Type. You must
  not wrap success responses in the problem+json envelope.
- Existing tests that assert the old error body shape (e.g.
  `{"detail": "job not found"}`) **must** be updated to assert the new
  problem+json body. These tests are in the existing test suite.
- No success-path test may change in any way.

---

## Half 2 — Request-scoped context propagation

Add a `RequestContext` (containing a `request_id` UUID string) that is
created once per HTTP request and propagated **explicitly as a parameter**
through the service and repository layers, so that every event published to
the event bus from an HTTP request carries the `request_id`.

### Required design

1. **`RequestContext` dataclass** — a frozen dataclass with a single field:
   `request_id: str`, defaulting to a freshly-generated UUID string. Defined
   in a new module (e.g. `app/context.py`).

2. **FastAPI dependency** — a dependency function `get_request_context` that
   creates or reuses a `RequestContext` for the current HTTP request (e.g.
   stored on `request.state`). The dependency must be declared as an
   `Annotated` type alias for use in route signatures.

3. **Explicit parameter threading** — every method in the service layer and
   repository layer that is called from an HTTP request must accept
   `ctx: RequestContext` as an explicit parameter. Worker-only methods (those
   called exclusively by the Prefect worker, not from HTTP handlers) may accept
   `ctx: RequestContext | None = None` to stay backward-compatible.

4. **Event propagation** — `create_job_event` must accept
   `ctx: RequestContext | None = None`. When `ctx` is not `None`, the returned
   event dict must include `"request_id": ctx.request_id`. The `job.created`
   event, which is published synchronously inside `JobService.create`, must
   carry the `request_id` of the originating HTTP request.

### Sealed propagation signature list

The following function signatures are sealed. Each must gain a `ctx` parameter
(or optional `ctx` parameter, for worker-only methods) in the solver's
implementation.

Generator command (run from `skills/agent-bench/cases/_base-taskflow/tree`):

```bash
grep -rn 'async def ' app/services/jobs.py app/repositories/jobs.py | sort
```

Generator output (frozen at `_base-taskflow@1`, run 2026-08-10):

```
app/repositories/jobs.py:113:    async def delete(self, job: Job) -> None:
app/repositories/jobs.py:20:    async def create(self, job_type: str, payload: dict[str, object]) -> Job:
app/repositories/jobs.py:26:    async def get(self, job_id: str) -> Job | None:
app/repositories/jobs.py:29:    async def mark_running(self, job: Job) -> Job:
app/repositories/jobs.py:35:    async def record_result(
app/repositories/jobs.py:54:    async def list(
app/repositories/jobs.py:64:    async def count(self, job_status: str | None) -> int:
app/repositories/jobs.py:71:    async def stats(self) -> dict[str, Any]:
app/services/jobs.py:53:    async def create(self, job_create: JobCreate) -> Job:
app/services/jobs.py:62:    async def get(self, job_id: str) -> Job:
app/services/jobs.py:68:    async def list(
app/services/jobs.py:87:    async def stats(self) -> dict[str, object]:
app/services/jobs.py:90:    async def delete(self, job_id: str) -> None:
```

Total: **13 signatures** across **2 files** (`app/services/jobs.py`,
`app/repositories/jobs.py`). Plus `create_job_event` in `app/events.py`
(1 additional site documented separately, not in grep output).

### Constraints

- `ctx` must be passed as an **explicit parameter** at every call site. You
  must not use `contextvars.ContextVar`, module-level globals, or any other
  ambient mechanism to propagate context.
- The `RequestContext` object must be created **once per HTTP request** and
  reused for all downstream calls within that request.
- Worker-called methods (`mark_running`, `record_result`) may accept
  `ctx: RequestContext | None = None` with `None` as default. They must not
  require a context that the worker cannot provide.
- No existing test may break. The existing tests do not check for `request_id`
  in events, so adding the field will not break them.

---

## Common constraints

- `uv run ruff check .` must exit 0.
- `uv run pytest -q` must exit 0 with all tests passing.

## What you do NOT need to do

- Change any success response body.
- Add documentation or a README.
- Change any database schema or job execution behaviour.
- Change any import that does not relate to error handling or context propagation.
