# Bug-hunt brief: Taskflow job service

This service passes its own test suite and both gates (`ruff check`, `pytest -q`). Audit it for defects that violate its documented behaviour, reproduced in the **Service contract** appendix below. For every defect you report, provide a reproduction — a failing test, a request transcript, or a command with its observed output. Report only what you can reproduce.

---

## Service contract

The following is the full behavioural contract for the Taskflow job service. Use it as the ground truth for your audit.

### Stack

Python 3.12 service. FastAPI + SQLite (via SQLAlchemy 2.0 async, aiosqlite). Prefect v3 processing pipeline. WebSocket event stream. Layered: routes → services → repositories; no business or storage logic in route handlers. Pydantic v2 request/response models. pytest with `asyncio_mode = "auto"`.

Gates: `uv run ruff check .` and `uv run pytest -q` must both exit 0.

### Routes

**Health and info**

- `GET /health` → `200` `{"status": "ok"}`
- `GET /` → `200` `{"service": "taskflow", "version": "0.1.0"}`

**Jobs CRUD**

- `POST /jobs` → `201` `JobResponse` with `status == "pending"`; `422` for unknown `type` or non-dict `payload`.
- `GET /jobs?status=&limit=&offset=` → `200` `{"jobs": [JobResponse, ...], "total": <int matching the filter>}`. Ordered `created_at` desc then `id` asc. `limit` default 20, range 1–100. `offset >= 0`. Out-of-range `limit`, negative `offset`, or invalid `status` → `422`.
- `GET /jobs/{id}` → `200 JobResponse` or `404 {"detail": "job not found"}`.
- `DELETE /jobs/{id}` → `204`; `409 {"detail": "job is running"}` when `status == "running"`; `404` when unknown.

**Stats**

- `GET /stats` → `200` with `jobs` (per-status counts + total), `by_type` (per-type counts), `avg_duration_s` (float or null).

**WebSocket**

- `WS /ws/jobs` (optional `?job_id=` filter): on connect sends `{"event": "connected"}`, then streams lifecycle events as JSON text frames.

### Job model

Fields: `id` (UUID4 str), `type` (one of `word_count | reverse | summary_stats`), `status` (one of `pending | running | succeeded | failed`), `payload` (dict), `result` (dict or null), `error` (str or null), `created_at` (UTC datetime, always set at creation), `started_at` (UTC datetime or null), `finished_at` (UTC datetime or null).

UTC datetimes must carry timezone information through the full request/response cycle, including after a DB round-trip.

### Lifecycle events

Published to the WebSocket bus: `job.created` on POST; `job.started`, `job.succeeded`, and `job.failed` from the worker. Each event: `{"event": "<name>", "job_id": "<id>", "status": "<status>", "ts": "<RFC3339 UTC>"}`.

Events must reflect durable state: a `job.created` event must not be published for a job that was never committed to the database.

### Processing

`word_count` payload `{"text": str}` → result `{"words": int, "chars": int}`.  
`reverse` payload `{"text": str}` → result `{"text": <reversed>}`.  
`summary_stats` payload `{"text": str}` → result `{"lines": int, "words": int, "unique_words": int}` (case-insensitive uniqueness).  
Missing or empty `payload["text"]` → job ends `failed` with a non-empty `error`; the flow itself must not raise.
