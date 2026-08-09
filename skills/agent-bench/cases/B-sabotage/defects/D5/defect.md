# D5 — Pagination returns last page instead of empty list past the end

## Criterion violated

From the `L-taskflow` specification (Jobs REST API):
> `GET /jobs?limit=&offset=` — pagination.

When `offset` exceeds the total number of matching jobs, the response must be an empty list. The spec does not define a "last page clamping" behaviour.

## Observable symptom

`GET /jobs?offset=100` (with 2 jobs in the DB) returns the 2 existing jobs instead of an empty list. The existing test uses `offset=1` with 3 jobs, which does not reach the boundary condition.

## Hunt-list category

boundary/rounding math — a clamping expression `offset = max(0, total - limit)` is applied when `offset >= total`, silently redirecting out-of-range requests to the last page rather than returning empty.
