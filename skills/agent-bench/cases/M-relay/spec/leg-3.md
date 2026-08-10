# M-relay — Session 3 of 3: Transaction history and operator docs

**This is the third and final session.** The repository contains accounts, credit, and
transfers from sessions 1 and 2. All conventions and design decisions from those sessions
apply throughout this session. Before implementing, recall your recorded decisions (money
field name, ID scheme, error body format, timestamp format) — this spec does not restate
them.

Gates carry forward: `uv run ruff check .` and `uv run pytest -q` must exit 0 after this
session.

---

## Transaction history

Record every balance movement and expose a paginated history per account.

### Data model

Add a `Transaction` model to `app/db/models.py`, table `transactions`:

- `id`: primary key generated with the **same scheme used by all other models**
- `account_id`: foreign key → `accounts.id`
- `amount_minor`: integer; positive value = credit to the account, negative value = debit
- `created_at`: UTC-aware datetime, using the **same persistence mechanism as all
  other `created_at` fields**

### Transaction recording

- Every `POST /accounts/{id}/credit` success appends one `Transaction` row for the account
  with `amount_minor` equal to the credited amount (positive).
- Every successful `POST /transfers` appends two `Transaction` rows:
  - One debit row for the source account: `amount_minor = -(transfer amount)` (negative)
  - One credit row for the destination account: `amount_minor = +(transfer amount)` (positive)
- A failed transfer must not append any transaction rows.

### `GET /accounts/{id}/transactions`

Query parameters: `limit: int`, `offset: int`.

- Unknown `{id}` → `404`; use **the same error body format as the existing account endpoints**.
- Response `200`:
  ```json
  {"items": [<Transaction>, ...], "total": <int>}
  ```
  Results ordered `created_at` descending (newest first).
- `limit` default `20`, maximum `100`; `limit > 100` → `422`.
- `offset` default `0`, non-negative; `offset` past the end returns an empty `items` list
  with the correct `total`.

Each `Transaction` in the response includes at minimum: `id`, `account_id`, `amount_minor`,
`created_at`. The `amount_minor` values are integers (same unit and type convention as
throughout the service); `created_at` uses the same timestamp format established in session 1.

### Conventions

The conventions from sessions 1 and 2 apply without restating them:
- Routes → services → repositories.
- Integer minor units; no floats.
- Async end to end.
- Error responses use the same HTTP codes and body format as the existing endpoints.
- New behaviour lands with tests including sad paths. Existing tests must remain green.

---

## Operator docs

`README.md` at the repo root (create or update):

- Quickstart: `uv sync`, then run the API with `uvicorn app.main:app`.
- An endpoint table covering every route in the service (all three sessions).
- The two gate commands (`uv run ruff check .` and `uv run pytest -q`).
