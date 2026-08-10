# M-relay — Session 1 of 3: Account management and credit

**This is the first of three sessions.** Each session runs with cold conversation context;
only the repository and your configured persistence mechanism survive to the next session.
Implement the features below, then — before you close this session — record the four design
decisions listed at the end. A solver whose persistence mechanism cannot recall those decisions
at the start of session 2 will be unable to implement a consistent service.

---

## Stack (fixed — do not substitute)

`uv` project with committed `uv.lock` and `.python-version` (3.12). Dependencies: `fastapi`,
`uvicorn`, `sqlalchemy[asyncio]`, `aiosqlite`, `pydantic-settings`; dev group: `pytest`,
`pytest-asyncio` (`asyncio_mode = "auto"` in `pyproject.toml`), `httpx`, `ruff`.
Layered structure: routes → services → repositories; no business or storage logic in route
handlers. SQLAlchemy 2.0 style (`Mapped[T]`, `mapped_column`, async engine,
`expire_on_commit=False`). Pydantic v2 request/response models, separate per direction.

## ASGI transport

The probe suite (hidden from you; placed at `tests/test_probe.py` by the evaluator) runs
against your app via an in-process ASGI transport using `starlette.testclient.TestClient`.
No live server is required or started. Your app factory must be importable as
`from app.main import create_app`.

## Gates

`uv run ruff check .` and `uv run pytest -q` must exit 0 after this session.
Tests must be fully self-contained: a throwaway SQLite file per test (tmp path via settings
override), no network access, no external services, no ordering dependencies.

## Global rules

Every acceptance bullet below is a literal check — reviewers walk them one by one.
Configuration only via `app/core/config.py` (`pydantic-settings`, env prefix `LEDGER_`);
no constant duplicated outside it.

**Money rule (non-negotiable):** all balances and amounts are integer minor units (e.g. cents).
No floats anywhere in the money path — not in the database schema, not in Python arithmetic,
not in the JSON response.

**Timezone rule:** all timestamps are UTC-aware and serialised as RFC 3339 / ISO 8601 with
explicit offset (e.g. `2026-08-07T10:30:00+00:00`). This must survive a SQLite persistence
round-trip — a `GET` after a `POST` must return a timezone-aware `created_at`, not a naive string.

## Account management

Stand up the app factory, settings, and the persistence layer.

- `app/main.py` exposes `create_app() -> FastAPI` and a module-level `app = create_app()`.
- `app/core/config.py` defines `Settings(BaseSettings)` with
  `db_path: str = ".data/ledger.db"` (env var `LEDGER_DB_PATH`) plus a `get_settings()`
  accessor that the app reads at startup and tests can override.
- `app/db/models.py`: SQLAlchemy 2.0 `Account` model, table `accounts`:
  `id` (str UUID4 primary key), `name` (str), `balance_minor` (int, **not** float, default 0),
  `created_at` (UTC-aware datetime).
- `app/db/session.py`: async engine on `sqlite+aiosqlite:///{db_path}` (parent dir created if
  missing), `async_sessionmaker(expire_on_commit=False)`, and `init_db()` that creates tables;
  `create_app()` runs `init_db()` via lifespan.
- `POST /accounts` body `{"name": str}` → `201`
  `{"id": str, "name": str, "balance_minor": 0, "created_at": <iso8601-aware>}`.
- `GET /accounts/{id}` → `200` with current `balance_minor` and `created_at`,
  or `404 {"detail": "account not found"}`.
- `POST /accounts/{id}/credit` body `{"amount_minor": int}`:
  - `amount_minor > 0` → `201`; increments `balance_minor` by the exact integer amount.
  - `amount_minor <= 0` → `422`.
  - Unknown `id` → `404 {"detail": "account not found"}`.

## Conventions (binding rules)

- **Layering and validation:** Routes → services → repositories. Route handlers hold zero
  business or storage logic; every write path goes through the service.
- **Money and arithmetic:** All balances and amounts are integer minor units. No floats
  anywhere — not in database columns (`Integer`, not `Float` or `Numeric`), not in Python
  arithmetic, not in JSON responses. Balance updates happen in a single atomic database
  transaction.
- **Async end to end:** Async SQLAlchemy sessions and async route handlers. Never call
  blocking I/O inside the event loop.
- **UTC everywhere:** Timestamps serialised as RFC 3339 with explicit offset. SQLite does not
  natively store timezone info; use a `TypeDecorator` (or equivalent) that stores the full
  ISO 8601 string and restores a UTC-aware `datetime` on read. A naive `datetime` returned
  from a `GET` is a defect.
- **Domain errors map to explicit HTTP codes** (400/404/409/422) with the exact bodies the
  spec defines. Never return 500 for a predictable domain condition.
- **Tests:** Self-contained: tmp-path SQLite per test, no network, no external services, no
  ordering dependencies. New behaviour lands with tests for the sad paths (404/422), not only
  the happy path.

---

## Required: record your design decisions before closing this session

Session 2 does not restate the following choices. It depends on you having recorded them.
Store them wherever your configuration persists information between sessions — a `DECISIONS.md`
file in the repository, a note in your memory server, or any other mechanism your setup
provides. Include enough detail that you can reproduce each choice without reading this file
again.

**Decision 1 — Money field name and storage type.**
Record the exact Python attribute name used for account balances, and the SQLAlchemy column
type (e.g. `Integer`). Both future sessions will use this field name and type without being
told it.

**Decision 2 — Account ID scheme.**
Record how account IDs are generated and stored (the Python type, the generation library or
function, and the SQLAlchemy column type). Future sessions create IDs for new models using
the same scheme.

**Decision 3 — Error response body format.**
Record the exact JSON key and value structure used for 4xx domain error responses (e.g. what
key holds the error message, and what strings are used for `account not found` and
`insufficient_funds`). Session 2 adds new error conditions that must match this format.

**Decision 4 — Timestamp format and persistence strategy.**
Record the exact serialisation format for `created_at` fields (timezone, offset notation) and
the mechanism used to make SQLite store and restore timezone-aware datetimes. Session 2 adds
a model with its own `created_at` that must behave identically.
