# M-relay — Session 2 of 3: Transfers with idempotency

> **Authoring note (v1):** This spec specifies `409 {"detail": "insufficient_funds"}` for
> the new error condition. That unavoidably reveals the `detail` key name used for all error
> bodies in the service, which slightly weakens continuity rows CC-03 and CC-06 on the
> key-name dimension — a solver can infer by analogy that 404 also uses `detail`. This is an
> accepted trade-off: the new behaviour must be specified explicitly, and the continuity
> signal is retained on the string-value dimension ("account not found") and on the UUID4 /
> timestamp decisions, which are not revealed here. Considered and accepted at v1 authoring.

**This is the second of three sessions.** The repository already contains the account
management and credit features from session 1. The conventions and design decisions you
recorded at the end of session 1 govern this session — this spec does not restate them.
Before implementing anything, recall your recorded decisions (money field name, ID scheme,
error body format, timestamp format) and verify they are consistent with the existing code.

Gates carry forward: `uv run ruff check .` and `uv run pytest -q` must exit 0 after this
session.

---

## Transfers with idempotency

Record transfers between accounts with exactly-once semantics enforced by a caller-supplied
idempotency key.

### Data model

Add a `Transfer` model to `app/db/models.py`, table `transfers`:

- `id`: primary key generated with the **same scheme as account IDs**
- `from_account_id`: foreign key → `accounts.id`
- `to_account_id`: foreign key → `accounts.id`
- `amount_minor`: integer, same unit as account balances
- `idempotency_key`: string, UNIQUE INDEX
- `request_body_hash`: string
- `created_at`: UTC-aware datetime, using the **same persistence mechanism as account
  `created_at`**

Do not expose `idempotency_key` or `request_body_hash` in any response body.

### `POST /transfers`

- **Required header:** `Idempotency-Key: <str>`; missing header → `400`.
  `400` is reserved for this missing application-layer header — FastAPI's default `422`
  is not the right code here.
- **Body:** `{"from_account_id": str, "to_account_id": str, "amount_minor": int}`
- `amount_minor <= 0` → `422`.
- Either account unknown → `404`; use **the same error body format as the existing
  account endpoints**. Do not invent a new format.
- `from_account_id` balance insufficient → `409 {"detail": "insufficient_funds"}`.
- **Success (first call):** atomically debit source and credit destination; return `201`
  with body:
  ```json
  {"id": "<same-scheme-as-account-ids>", "from_account_id": str, "to_account_id": str,
   "amount_minor": int, "created_at": "<same-timestamp-format-as-accounts>"}
  ```
- **Replay — same `Idempotency-Key` + identical body:** return `200` with the same transfer
  record (same `id`); do **not** debit or credit again.
- **Replay — same `Idempotency-Key` + different body:** return `409`.
- All balance updates (debit source, credit destination) happen atomically; a failed transfer
  must leave both balances unchanged.

The idempotency check uses a hash of the canonical request body (JSON with keys sorted, no
extra whitespace). Store this hash alongside the `idempotency_key`.

The idempotency check must happen before any write — detect conflicts and return early rather
than writing and then trying to undo.

### Conventions

The conventions from session 1 apply without restating them:
- Routes → services → repositories; no business logic in route handlers.
- Integer minor units everywhere in the money path; no floats.
- Insufficient-funds check inside the same transaction that modifies balances.
- Async end to end.
- Domain errors return the same HTTP codes and body format used in session 1.
- New behaviour lands with tests for the sad paths (400/404/409/422), not only the happy path.
  Existing tests from session 1 must remain green without modification.
