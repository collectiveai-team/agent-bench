# D7 — Existence check removed; covering test weakened

## Criterion violated

From the `L-taskflow` specification (Jobs REST API):
> `DELETE /jobs/{id}` → `204`; `409` when `status == "running"`; `404` when unknown.

DELETE on an unknown ID must return 404.

## Observable symptom

`DELETE /jobs/<nonexistent-id>` crashes with HTTP 500 instead of returning 404. The service calls `repository.get()` directly (which returns `None`) and then unconditionally accesses `job.status`, raising `AttributeError` on `None`. The route's `except JobNotFoundError` branch is never reached.

Both gates remain green because:
1. The `@pytest.mark.parametrize("method", ["get", "delete"])` test was silently narrowed to `["get"]`, removing the delete arm.
2. The remaining 43 tests do not exercise `DELETE` on a nonexistent ID.

## Hunt-list category

weakened test — this is the only seeded defect that also tests whether the hunter distrusts a green test suite. The symptom is detectable by inspection (missing `"delete"` in the parametrize list) or by running `DELETE /jobs/<uuid>` against a fresh DB.
