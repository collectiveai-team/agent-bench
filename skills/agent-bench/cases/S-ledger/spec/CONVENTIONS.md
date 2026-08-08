# Ledger conventions (hard rules)

These are failure-mode rules, not style suggestions. The critic and reviewers
reject code that violates them even when tests pass.

## Layering and validation

- Routes → services → repositories. Route handlers hold zero business or
  storage logic; every write path (including credit and transfer paths) goes
  through the service so validation cannot be bypassed at the router.
- Partial updates must never reset omitted fields — build updates from
  `model_dump(exclude_unset=True)` or explicit field lists.
- Join and look up by `id`, never by name or other mutable fields.
- Single source of truth for constants (status strings, limit bounds, env
  prefix): define once in `app/core/config.py` or one enum module and import
  it everywhere, including tests.

## Money and arithmetic

- All balances and amounts are **integer** minor units. No floats anywhere in
  the money path — not in the database columns (`Integer`, not `Float` or
  `Numeric`), not in Python arithmetic, not in JSON responses.
- Balance updates (debit + credit for a transfer) happen in a single atomic
  database transaction. A partial update that credits the destination but not
  the source (or vice versa) is data corruption.
- Insufficient-funds checking must happen inside the same transaction that
  modifies the balance; checking outside and then writing inside creates a
  race window even with SQLite.

## Idempotency keys

- The idempotency check must happen before any write, not after. Check the key,
  detect conflicts, and return early — do not write and then try to undo.
- The request body hash must cover the canonical body (sorted keys, no extra
  whitespace). A hash computed from raw bytes without normalisation can produce
  false conflicts on equivalent bodies.
- Do not expose the idempotency key or body hash in any response body.

## Async and concurrency

- Async end to end: async SQLAlchemy sessions and async route handlers. Never
  call blocking I/O inside the event loop.
- There is no background worker or websocket in this service. Any `asyncio`
  task created outside a request must be cancelled and awaited on shutdown.

## Data and errors

- UTC everywhere; timestamps serialised as RFC 3339 with explicit offset.
  SQLite does not natively store timezone info; use a `TypeDecorator` (or
  equivalent) that stores the full ISO 8601 string and restores a UTC-aware
  `datetime` on read. A naive `datetime` returned from a `GET` is a defect.
- Domain errors map to explicit HTTP codes (400/404/409/422) with the exact
  bodies the spec defines. Never return 500 for a predictable domain condition.
- `400` is reserved for the missing `Idempotency-Key` header — FastAPI's
  default 422 unprocessable body is not the right code for a missing
  application-layer protocol header.

## Tests

- Self-contained: tmp-path SQLite per test, no network, no external services,
  no ordering dependencies.
- Existing consumers keep working: never change a shipped response shape,
  status code, or field name; tests from earlier features must stay green
  untouched.
- New behavior lands with tests for the sad paths (400/404/409/422), not only
  the happy path.
