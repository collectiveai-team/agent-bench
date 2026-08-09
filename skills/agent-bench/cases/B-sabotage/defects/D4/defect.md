# D4 — Type filter queries against the wrong column

## Criterion violated

From the `L-taskflow` specification (Jobs REST API):
> `GET /jobs?status=&limit=&offset=` → filtered list.

A `?type=` filter was added to this endpoint, but it filters `Job.status` instead of `Job.type`. Since no job ever has a status equal to a type name (`"word_count"`, `"reverse"`, `"summary_stats"`), the filter always returns an empty list.

## Observable symptom

`GET /jobs?type=word_count` returns `{"jobs": [], "total": 0}` even when `word_count` jobs exist. Existing tests do not exercise the `?type=` parameter, so both gates stay green.

## Hunt-list category

join on name instead of id — the WHERE clause compares the wrong string column: `Job.status == job_type` instead of `Job.type == job_type`.
