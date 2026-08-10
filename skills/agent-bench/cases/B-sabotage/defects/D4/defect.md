# D4 — Stats aggregation uses wrong grouping key for by_type counts

## Criterion violated

From the `L-taskflow` specification (Stats endpoint):
> `GET /stats` → `200` `{..., "by_type": {"word_count": int, "reverse": int, "summary_stats": int}, ...}` — computed with SQL aggregates in the repository.

The `by_type` counts must reflect how many jobs exist for each job **type**
(`word_count`, `reverse`, `summary_stats`). Counting by the wrong column produces
all-zero type counts because no job will ever have a status equal to a type name.

## Observable symptom

`GET /stats` returns `"by_type": {"word_count": 0, "reverse": 0, "summary_stats": 0}`
regardless of how many jobs of each type exist. The aggregation in
`app/repositories/jobs.py` compares `Job.status == job_type` instead of
`Job.type == job_type`. Since status values (`pending`, `running`, `succeeded`,
`failed`) never equal type names, the CASE expression never fires.

The tests that would catch this (`test_stats_returns_sql_aggregates` and
`test_public_inline_lifecycle`) were weakened to check only that the `by_type`
keys are present, not that their values are correct.

## Hunt-list category

wrong grouping key — the WHERE clause inside the type-count aggregate compares the
wrong column: `Job.status == job_type` instead of `Job.type == job_type`. The fix
is a one-token change at `app/repositories/jobs.py` line 77.
