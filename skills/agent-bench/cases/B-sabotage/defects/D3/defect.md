# D3 — Partial update overwrites absent fields with None

## Criterion violated

From the `L-taskflow` specification (Jobs REST API):
> Existing behavior from earlier features must keep working when later features land.

A partial-update endpoint (`PATCH /jobs/{id}`) must not overwrite fields the caller did not supply.

## Observable symptom

`PATCH /jobs/{id}` with `{"payload": {"text": "new"}}` silently clears the `error` field (sets it to `null`) even though `error` was not included in the request. Fields not present in the body are indistinguishable from fields explicitly set to `null`.

## Hunt-list category

partial-update data loss — `job_update.model_dump()` (without `exclude_unset=True`) serializes every schema field including those the client never sent, overwriting DB-side values with `None`.
