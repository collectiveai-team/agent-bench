# Ledger: money account service (FastAPI + SQLite)

A self-contained Python 3.12 service that manages named accounts with integer
minor-unit balances, accepts credit operations, and records transfers between
accounts with idempotency-key protection. This file is the full contract; the
governance roles review against it verbatim.

**Stack (fixed — do not substitute):** `uv` project with committed `uv.lock`
and `.python-version` (3.12). Dependencies: `fastapi`, `uvicorn`,
`sqlalchemy[asyncio]`, `aiosqlite`, `pydantic-settings`; dev group: `pytest`,
`pytest-asyncio` (`asyncio_mode = "auto"` in `pyproject.toml`), `httpx`, `ruff`.
Layered structure: routes → services → repositories; no business or storage
logic in route handlers. SQLAlchemy 2.0 style (`Mapped[T]`, `mapped_column`,
async engine, `expire_on_commit=False`). Pydantic v2 request/response models,
separate per direction.

**ASGI transport:** the probe suite (hidden from you; placed at
`tests/test_probe.py` by the evaluator) runs against your app via an in-process
ASGI transport using `starlette.testclient.TestClient`. No live server is
required or started. Your app factory must be importable as
`from app.main import create_app`.

**Gates:** `uv run ruff check .` and `uv run pytest -q` must exit 0 after every
feature. Tests must be fully self-contained: a throwaway SQLite file per test
(tmp path via settings override), no network access, no external services, no
ordering dependencies.

**Global rules:** every acceptance bullet below is a literal check — reviewers
walk them one by one. Existing behavior from earlier features must keep working
when later features land. Configuration only via `app/core/config.py`
(`pydantic-settings`, env prefix `LEDGER_`); no constant duplicated outside it.

**Money rule (non-negotiable):** all balances and amounts are integer minor
units (e.g. cents). No floats anywhere in the money path — not in the database
schema, not in Python arithmetic, not in the JSON response.

**Timezone rule:** all timestamps are UTC-aware and serialised as RFC 3339 /
ISO 8601 with explicit offset (e.g. `2026-08-07T10:30:00+00:00`). This must
survive a SQLite persistence round-trip — a `GET` after a `POST` must return a
timezone-aware `created_at`, not a naive string.

## Account management

Stand up the app factory, settings, and the persistence layer.

- `app/main.py` exposes `create_app() -> FastAPI` and a module-level
  `app = create_app()`.
- `app/core/config.py` defines `Settings(BaseSettings)` with
  `db_path: str = ".data/ledger.db"` (env var `LEDGER_DB_PATH`) plus a
  `get_settings()` accessor that the app reads at startup and tests can
  override.
- `app/db/models.py`: SQLAlchemy 2.0 `Account` model, table `accounts`:
  `id` (str UUID4 primary key), `name` (str), `balance_minor` (int, **not**
  float, default 0), `created_at` (UTC-aware datetime).
- `app/db/session.py`: async engine on `sqlite+aiosqlite:///{db_path}` (parent
  dir created if missing), `async_sessionmaker(expire_on_commit=False)`, and
  `init_db()` that creates tables; `create_app()` runs `init_db()` via
  lifespan.
- `POST /accounts` body `{"name": str}` → `201`
  `{"id": str, "name": str, "balance_minor": 0, "created_at": <iso8601-aware>}`.
- `GET /accounts/{id}` → `200` with current `balance_minor` and `created_at`,
  or `404 {"detail": "account not found"}`.
- `POST /accounts/{id}/credit` body `{"amount_minor": int}`:
  - `amount_minor > 0` → `201`; increments `balance_minor` by the exact integer
    amount.
  - `amount_minor <= 0` → `422`.
  - Unknown `id` → `404 {"detail": "account not found"}`.

## Transfers with idempotency keys

Record transfers between accounts with exactly-once semantics enforced by a
caller-supplied idempotency key.

- `app/db/models.py`: add `Transfer` model, table `transfers`:
  `id` (str UUID4 PK), `from_account_id` (str FK → `accounts.id`),
  `to_account_id` (str FK → `accounts.id`), `amount_minor` (int),
  `idempotency_key` (str, UNIQUE INDEX), `request_body_hash` (str),
  `created_at` (UTC-aware datetime).
- `POST /transfers`
  - Required header: `Idempotency-Key: <str>`; missing header → `400`.
  - Body: `{"from_account_id": str, "to_account_id": str, "amount_minor": int}`.
  - `amount_minor <= 0` → `422`.
  - Either account unknown → `404 {"detail": "account not found"}`.
  - `from_account_id` balance insufficient → `409 {"detail": "insufficient_funds"}`.
  - Success → `201`
    `{"id": str, "from_account_id": str, "to_account_id": str,
    "amount_minor": int, "created_at": <iso8601-aware>}`.
  - Replay — same `Idempotency-Key` + **identical** body → `200` and the same
    transfer record (same `id`); does **not** debit or credit again.
  - Replay — same `Idempotency-Key` + **different** body → `409`.
  - All balance updates (debit source, credit destination) happen atomically;
    a failed transfer must leave both balances unchanged.

  The idempotency check is based on a hash of the canonical request body (JSON
  with keys sorted, no extra whitespace). Store the hash alongside the
  `idempotency_key` in the `transfers` table.

## Transaction history

Record every balance movement and expose a paginated history per account.

- `app/db/models.py`: add `Transaction` model, table `transactions`:
  `id` (str UUID4 PK), `account_id` (str FK → `accounts.id`),
  `amount_minor` (int, positive = credit, negative = debit), `created_at`
  (UTC-aware datetime).
- Every credit (`POST /accounts/{id}/credit`) appends one `Transaction` row for
  the account.
- Every successful transfer appends two `Transaction` rows: one debit
  (`-amount_minor`) for the source account and one credit (`+amount_minor`) for
  the destination account.
- `GET /accounts/{id}/transactions?limit=<int>&offset=<int>` → `200`
  `{"items": [<Transaction>, ...], "total": <int>}`, results ordered
  `created_at` descending (newest first).
  - `limit` default `20`, maximum `100`; `limit > 100` → `422`.
  - `offset` default `0`, non-negative; `offset` past the end returns an empty
    `items` list with the correct `total`.
  - Unknown `id` → `404 {"detail": "account not found"}`.

## Operator docs

- `README.md` at the repo root: quickstart (`uv sync`, run API via
  `uvicorn app.main:app`), an endpoint table covering every route above, and
  the two gate commands.
