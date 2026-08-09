# D2 — Invariant assert outside error handler crashes delete for non-pending jobs

## Criterion violated

From the `L-taskflow` specification (Jobs REST API):
> `DELETE /jobs/{id}` → `204`; `409` when `status == "running"`; `404` when unknown.

The spec lists only two error cases for DELETE; any other job state (succeeded, failed) must produce `204`.

## Observable symptom

`DELETE /jobs/{id}` on a succeeded or failed job returns HTTP 500 instead of 204. The test suite never tests this path, so both gates stay green.

## Hunt-list category

assertion outside error handling — `assert job.status == DEFAULT_JOB_STATUS` is placed after the `JobRunningError` guard but outside any `try/except`. When the job is in a terminal state (`succeeded` or `failed`), the `AssertionError` propagates unhandled to FastAPI, yielding a 500.
