# Taskflow

Taskflow is an async job service built with FastAPI, SQLite, SQLAlchemy, and Prefect.
It persists text-processing jobs, runs them inline or through a Prefect deployment,
and streams lifecycle events over WebSockets.

## Quickstart

Install the locked project dependencies:

```bash
uv sync
```

Run the API with the default inline worker:

```bash
uv run uvicorn app.main:app
```

For Prefect mode, run the API and worker in separate terminals with the same
configuration:

```bash
TASKFLOW_WORKER_MODE=prefect uv run uvicorn app.main:app
```

```bash
TASKFLOW_WORKER_MODE=prefect uv run python -m app.worker
```

The service listens on `http://127.0.0.1:8000` by default. Its SQLite database is
stored at `.data/taskflow.db` unless `TASKFLOW_DB_PATH` is set.

## Configuration

| Environment variable | Default | Description |
| --- | --- | --- |
| `TASKFLOW_DB_PATH` | `.data/taskflow.db` | SQLite database file path. |
| `TASKFLOW_WORKER_MODE` | `inline` | Processing mode: `inline` or `prefect`. |

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Return service metadata. |
| `GET` | `/health` | Return service health. |
| `POST` | `/jobs` | Create and enqueue a job. |
| `GET` | `/jobs` | List jobs with optional `status`, `limit`, and `offset` query parameters. |
| `GET` | `/jobs/{id}` | Fetch one job. |
| `DELETE` | `/jobs/{id}` | Delete a job unless it is running. |
| `GET` | `/stats` | Return status/type counts and average terminal duration. |
| `WS` | `/ws/jobs` | Stream lifecycle events, optionally filtered by `job_id`. |

Supported job types are `word_count`, `reverse`, and `summary_stats`. Each accepts a
JSON payload containing a non-empty `text` string:

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H 'content-type: application/json' \
  -d '{"type":"word_count","payload":{"text":"hello taskflow"}}'
```

## WebSocket

Connect before creating a job to observe its complete lifecycle. Omit `job_id` to
receive every job event, or include it to filter the stream:

```javascript
const socket = new WebSocket("ws://127.0.0.1:8000/ws/jobs?job_id=<job-id>");

socket.addEventListener("message", (message) => {
  console.log(JSON.parse(message.data));
});
```

The first frame is `{"event":"connected"}`. Job frames use the event names
`job.created`, `job.started`, `job.succeeded`, and `job.failed`.

## Verification

```bash
uv run ruff check .
uv run pytest -q
```
