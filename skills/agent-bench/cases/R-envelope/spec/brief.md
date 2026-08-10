# R-envelope — task brief

You are working in a copy of the `_base-taskflow@1` service: a FastAPI + SQLite
job-execution service with a WebSocket event stream and a Prefect worker. The
suite ships 44 passing tests. Both gates must remain green when you are done.

## Your task

Migrate every error response the service can produce to the RFC 7807
Problem Details for HTTP APIs format, without changing any success response
and without breaking the existing test suite.

## Required envelope shape

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

## Error paths you must cover

The service has the following error-producing paths; all must be migrated:

1. **404 — job not found** when `GET /jobs/{job_id}` is called with an unknown
   id.
2. **404 — job not found** when `DELETE /jobs/{job_id}` is called with an
   unknown id.
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

## Constraints

- Every error response must use `application/problem+json`. No error path may
  return `application/json`.
- Every success response (2xx) must be unchanged: the same body shape, the
  same HTTP status code, and `application/json` as the Content-Type. You must
  not wrap success responses in the problem+json envelope.
- Existing tests that assert the old error body shape (e.g.
  `{"detail": "job not found"}`) **must** be updated to assert the new
  problem+json body. These tests are in the existing test suite.
- No success-path test may change in any way.
- `uv run ruff check .` must exit 0.
- `uv run pytest -q` must exit 0 with all tests passing.

## What you do NOT need to do

- Change any success response.
- Add documentation or a README.
- Change any service logic, database schema, or job execution behaviour.
- Change any import that does not relate to error handling.
