# D3 — Status-transition overwrites unset fields with None

## Criterion violated

From the `L-taskflow` specification (Jobs REST API):
> `GET /jobs/{id}` → `200`, or `404 {"detail": "job not found"}`.

Existing data on a job record must be preserved across status transitions. A job's
`payload` must read back through `GET /jobs/{id}` with the same value it had at
creation, even after the job reaches a terminal state.

## Observable symptom

After a `word_count` job succeeds, `GET /jobs/{job_id}` returns `"payload": {}` —
the original payload (`{"text": "hello world"}`) has been silently overwritten with
an empty dict. The `record_result` method in `app/repositories/jobs.py` wraps the
terminal state in a `_JobRecord` Pydantic model and calls `model_dump()` without
`exclude_unset=True`; the model's `payload` field defaults to `{}`, so every field
in `model_dump()` is written back to the ORM object, including the unset `payload`.

## Hunt-list category

partial-update data loss — `model_dump()` without `exclude_unset=True` serializes
every schema field (including those the caller never supplied), overwriting DB-side
values with their Python defaults.
