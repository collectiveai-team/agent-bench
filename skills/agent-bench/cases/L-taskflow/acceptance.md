# Acceptance criteria — L-taskflow

Frozen item count: **34**

Each row is one observable criterion. The evaluator runs `verification_command` verbatim in the root of a fresh clone of the solver's branch and determines pass/fail from the observed output alone.

Curl-based items require the server to be running on `http://localhost:8000`; the evaluator starts it with `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` in a background process before walking acceptance items.

Items whose `verification_command` runs `uv run pytest probes/test_probe.py` rely on the probe file having been copied to `probes/test_probe.py` at the clone root by Stage 2 step 4. These items run independently of the live server on port 8000 — the probe uses `TestClient` in-process.

| id | criterion | verification_command |
|---|---|---|
| AC-01 | `GET /health` returns HTTP 200. | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health` |
| AC-02 | `GET /health` response body is exactly `{"status":"ok"}`. | `curl -s http://localhost:8000/health` |
| AC-03 | `GET /` returns HTTP 200. | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/` |
| AC-04 | `GET /` response body contains `"service":"taskflow"` and `"version":"0.1.0"`. | `curl -s http://localhost:8000/ \| python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('service'), d.get('version'))"` |
| AC-05 | The SQLite database file is created under `.data/` after startup (default `db_path`). | `test -f .data/taskflow.db && echo present` |
| AC-06 | `TASKFLOW_DB_PATH` and `TASKFLOW_WORKER_MODE` env vars are read at startup and override the defaults. | `python3 -c "import os; os.environ['TASKFLOW_DB_PATH']='/tmp/actest.db'; os.environ['TASKFLOW_WORKER_MODE']='inline'; from app.core.config import get_settings; s=get_settings(); print(s.db_path, s.worker_mode)"` |
| note | AC-06 requires that `get_settings` re-reads the environment (or the module is reloaded) when called from a fresh interpreter. If `get_settings` uses `@lru_cache`, the probe resets the cache via `get_settings.cache_clear()` before each test. | — |
| AC-07 | `POST /jobs` with a valid `word_count` job returns HTTP 201. | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/jobs -H 'Content-Type: application/json' -d '{"type":"word_count","payload":{"text":"hello world"}}'` |
| AC-08 | `POST /jobs` response body contains `id`, `type`, `status`, `payload`, `result`, `error`, `created_at`, `started_at`, and `finished_at` fields, with `status == "pending"`. | `curl -s -X POST http://localhost:8000/jobs -H 'Content-Type: application/json' -d '{"type":"reverse","payload":{"text":"hi"}}' \| python3 -c "import sys,json; d=json.load(sys.stdin); print(sorted(d.keys()), d.get('status'))"` |
| AC-09 | `POST /jobs` with an unknown `type` returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/jobs -H 'Content-Type: application/json' -d '{"type":"no_such_type","payload":{"text":"x"}}'` |
| AC-10 | `POST /jobs` with a non-dict `payload` returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/jobs -H 'Content-Type: application/json' -d '{"type":"word_count","payload":"not a dict"}'` |
| AC-11 | `GET /jobs` returns HTTP 200 with a body containing exactly `"jobs"` and `"total"` as top-level keys. | `curl -s http://localhost:8000/jobs \| python3 -c "import sys,json; d=json.load(sys.stdin); print(sorted(d.keys()))"` |
| AC-12 | `GET /jobs?limit=0` returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8000/jobs?limit=0'` |
| AC-13 | `GET /jobs?limit=101` returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8000/jobs?limit=101'` |
| AC-14 | `GET /jobs?offset=-1` returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8000/jobs?offset=-1'` |
| AC-15 | `GET /jobs?status=bogus` returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8000/jobs?status=bogus'` |
| AC-16 | `GET /jobs/{id}` for a non-existent UUID returns HTTP 404 with body `{"detail":"job not found"}`. | `curl -s http://localhost:8000/jobs/00000000-0000-0000-0000-000000000000` |
| AC-17 | `DELETE /jobs/{id}` for a non-existent UUID returns HTTP 404 with body `{"detail":"job not found"}`. | `curl -s -X DELETE http://localhost:8000/jobs/00000000-0000-0000-0000-000000000000` |
| AC-18 | `DELETE /jobs/{id}` when `status == "running"` returns HTTP 409 with body `{"detail":"job is running"}`; after resetting to `succeeded` the same job deletes with 204; a subsequent `GET` returns 404. | `uv run pytest probes/test_probe.py -q -k test_409_delete_running_then_204 2>&1 \| tail -2` |
| AC-19 | A `word_count` job completes with `{"words": <int>, "chars": <int>}` in `result`; exact math: `"Hello  world hello"` (double space) → `{"words": 3, "chars": 18}`. | `uv run pytest probes/test_probe.py -q -k test_result_word_count_exact 2>&1 \| tail -2` |
| AC-20 | A `reverse` job completes with `{"text": <reversed string>}` in `result`; `"abc def"` → `{"text": "fed cba"}`. | `uv run pytest probes/test_probe.py -q -k test_result_reverse_exact 2>&1 \| tail -2` |
| AC-21 | A `summary_stats` job completes with `{"lines": <int>, "words": <int>, "unique_words": <int>}`, counting unique words case-insensitively. | `uv run pytest probes/test_probe.py -q -k test_result_summary_stats_exact 2>&1 \| tail -2` |
| AC-22 | A `summary_stats` job submitted with an empty payload or `payload["text"] == ""` reaches `status == "failed"` with a non-empty `error` field, `result == null`, and a non-null `finished_at`. | `uv run pytest probes/test_probe.py -q -k test_failed_job_contract 2>&1 \| tail -2` |
| AC-23 | The Prefect flow is importable as `app.worker.flow.process_job` and its `.name` attribute is `"process-job"`. | `python3 -c "from app.worker.flow import process_job; print(process_job.name)"` |
| AC-24 | `process_job.to_deployment(name='taskflow').name` equals `"taskflow"`. | `python3 -c "from app.worker.flow import process_job; d=process_job.to_deployment(name='taskflow'); print(d.name)"` |
| AC-25 | Connecting to `WS /ws/jobs` delivers `{"event":"connected"}` as the first frame; subsequent frames for a created job arrive in the order `job.created → job.started → job.succeeded`, each carrying `job_id`, `status`, and `ts`. | `uv run pytest probes/test_probe.py -q -k test_ws_event_order 2>&1 \| tail -2` |
| AC-26 | The `?job_id=` WebSocket filter suppresses events for jobs with a different id. | `uv run pytest probes/test_probe.py -q -k test_ws_filter_excludes_other_jobs 2>&1 \| tail -2` |
| AC-27 | `GET /stats` returns HTTP 200 with top-level keys `jobs`, `by_type`, and `avg_duration_s`. | `curl -s http://localhost:8000/stats \| python3 -c "import sys,json; d=json.load(sys.stdin); print(sorted(d.keys()))"` |
| AC-28 | `GET /stats` returns `avg_duration_s: null` when no jobs have reached a terminal state. | `uv run pytest probes/test_probe.py -q -k test_stats_null_avg_when_no_terminal_jobs 2>&1 \| tail -2` |
| AC-29 | `GET /stats` counts per-status and per-type correctly across a mixed set of completed jobs. | `uv run pytest probes/test_probe.py -q -k test_stats_math 2>&1 \| tail -2` |
| AC-30 | `GET /jobs` lists results ordered by `created_at` descending; `total` reflects the applied filter, not the page size. | `uv run pytest probes/test_probe.py -q -k test_list_ordering_and_totals 2>&1 \| tail -2` |
| AC-31 | `README.md` exists at the repository root. | `test -f README.md && echo present` |
| AC-32 | `README.md` contains quickstart instructions covering `uv sync`, running the API via `uvicorn app.main:app`, and running the worker via `python -m app.worker`. | `python3 -c "t=open('README.md').read(); print('ok' if all(s in t for s in ['uv sync','app.main:app','app.worker']) else 'missing')"` |
| AC-33 | `README.md` contains a WebSocket usage example and an endpoint table that includes `/ws/jobs`. | `python3 -c "t=open('README.md').read(); print('ok' if '/ws/jobs' in t and 'GET /jobs' in t else 'missing')"` |
| AC-34 | `uv run ruff check .` exits 0. | `uv run ruff check . && echo exit:0 || echo exit:1` |
