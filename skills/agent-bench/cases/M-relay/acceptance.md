# Acceptance criteria — M-relay

Frozen item count: **27**

The final state of M-relay leg 3 is the complete S-ledger contract. These 27 items are
identical in criterion and verification_command to the S-ledger acceptance criteria, applied
to the leg-3 repository. No acceptance row runs a mandatory gate command (`uv run ruff check .`
or bare `uv run pytest -q`) — those gates are scored separately.

Each row is one observable criterion. The evaluator runs `verification_command` verbatim in
the root of a fresh clone of the solver's branch and determines pass/fail from the observed
output alone.

Curl-based items require the server to be running on `http://localhost:8000`; the evaluator
starts it with `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` in a background
process before walking acceptance items.

Items whose `verification_command` runs `uv run pytest probes/test_probe.py` rely on the
probe file having been copied to `probes/test_probe.py` at the clone root by Stage 2 step 4.
These items run independently of the live server — the probe uses `TestClient` in-process.

**Probe-as-acceptance pattern.** Some items below invoke a single probe test as their
verification command (e.g. `uv run pytest probes/test_probe.py -q -k <name>`). This pattern
is used only where no stateless shell command can observe the criterion: exact balance
arithmetic after a transfer, idempotent-replay semantics, transaction row recording, and
timezone survival across a persistence round-trip all require multi-step state. Dropping
these would leave entire spec sections with no acceptance coverage. Formula consequence: an
acceptance item that is a probe test moves both `acceptance_share × 30` and `probe_share × 10`
in the `scoring.md` formula — those two terms are not fully independent for this case.

**Scope of coverage.** The 27 items cover all three legs:
- AC-01 through AC-08: Leg-1 (account management and credit)
- AC-09 through AC-16: Leg-2 (transfers with idempotency)
- AC-17 through AC-27: Leg-3 (transaction history and operator docs)

---

## Leg 1 — Account management and credit

| id | criterion | verification_command |
|---|---|---|
| AC-01 | `POST /accounts` with a valid body returns HTTP 201. | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/accounts -H 'Content-Type: application/json' -d '{"name":"test-ac01"}'` |
| AC-02 | `POST /accounts` response body contains `id`, `name`, `balance_minor`, and `created_at` fields. | `curl -s -X POST http://localhost:8000/accounts -H 'Content-Type: application/json' -d '{"name":"test-ac02"}' \| python3 -c "import sys,json; d=json.load(sys.stdin); print(sorted(d.keys()))"` |
| AC-03 | A newly created account has `balance_minor == 0`. | `curl -s -X POST http://localhost:8000/accounts -H 'Content-Type: application/json' -d '{"name":"test-ac03"}' \| python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('balance_minor'))"` |
| AC-04 | The `created_at` on a new account is a timezone-aware ISO 8601 string (contains `+` or ends with `Z`). | `curl -s -X POST http://localhost:8000/accounts -H 'Content-Type: application/json' -d '{"name":"test-ac04"}' \| python3 -c "import sys,json; d=json.load(sys.stdin); ts=d.get('created_at',''); print('aware' if ('+' in ts or ts.endswith('Z')) else 'naive')"` |
| AC-05 | `GET /accounts/{id}` for an unknown id returns HTTP 404 with body `{"detail":"account not found"}`. | `curl -s http://localhost:8000/accounts/00000000-0000-0000-0000-000000000000` |
| AC-06 | `POST /accounts/{id}/credit` with a positive `amount_minor` returns HTTP 201; re-fetching the account shows the updated balance. | `uv run pytest probes/test_probe.py -q -k test_credit_then_balance 2>&1 \| tail -2` |
| AC-07 | `POST /accounts/{id}/credit` with `amount_minor == 0` returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/accounts/$(curl -s -X POST http://localhost:8000/accounts -H 'Content-Type: application/json' -d '{"name":"ac07"}' \| python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")/credit -H 'Content-Type: application/json' -d '{"amount_minor":0}'` |
| AC-08 | `POST /accounts/{id}/credit` for an unknown account returns HTTP 404. | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/accounts/00000000-0000-0000-0000-000000000000/credit -H 'Content-Type: application/json' -d '{"amount_minor":100}'` |

## Leg 2 — Transfers with idempotency

| id | criterion | verification_command |
|---|---|---|
| AC-09 | `POST /transfers` without the `Idempotency-Key` header returns HTTP 400. | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/transfers -H 'Content-Type: application/json' -d '{"from_account_id":"00000000-0000-0000-0000-000000000000","to_account_id":"00000000-0000-0000-0000-000000000001","amount_minor":50}'` |
| AC-10 | `POST /transfers` with `amount_minor == 0` and the `Idempotency-Key` header present returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/transfers -H 'Content-Type: application/json' -H 'Idempotency-Key: ac10-key' -d '{"from_account_id":"00000000-0000-0000-0000-000000000000","to_account_id":"00000000-0000-0000-0000-000000000001","amount_minor":0}'` |
| note | AC-09 and AC-10 use UUID-shaped account ids that do not exist in the database. The missing-header check (AC-09) and body-validation check (AC-10) must fire before any database lookup — consistent with the convention that application-layer header checks and Pydantic body validation precede business logic. | — |
| AC-11 | `POST /transfers` with an unknown `from_account_id` returns HTTP 404; `POST /transfers` with an unknown `to_account_id` returns HTTP 404. | `uv run pytest probes/test_probe.py -q -k test_unknown_account 2>&1 \| tail -2` |
| note | AC-11 uses the probe because checking unknown `to_account_id` in isolation requires a pre-funded source account; both cases are in one probe test function and cannot fail independently at the probe level. | — |
| AC-12 | `POST /transfers` with a source balance insufficient for the requested amount returns HTTP 409 with `{"detail": "insufficient_funds"}`; both the source and destination balances remain unchanged after the failed transfer. | `uv run pytest probes/test_probe.py -q -k test_insufficient_funds 2>&1 \| tail -2` |
| AC-13 | A successful `POST /transfers` debits the source and credits the destination by exactly `amount_minor` integer minor units; `balance_minor` values returned by `GET /accounts/{id}` are integers, not floats. | `uv run pytest probes/test_probe.py -q -k test_transfer_moves_exact_minor_units 2>&1 \| tail -2` |
| AC-14 | A successful `POST /transfers` appends one debit transaction (`amount_minor == -<amount>`) to the source account and one credit transaction (`amount_minor == +<amount>`) to the destination account, visible via `GET /accounts/{id}/transactions`. | `uv run pytest probes/test_probe.py -q -k test_transfer_records_transaction_rows 2>&1 \| tail -2` |
| AC-15 | Replaying a `POST /transfers` with the same `Idempotency-Key` and identical body returns HTTP 200 with the same `id` as the first response; the source and destination balances are not changed by the replay. | `uv run pytest probes/test_probe.py -q -k test_idempotent_replay_same_body_returns_same_id_and_moves_once 2>&1 \| tail -2` |
| AC-16 | Replaying a `POST /transfers` with the same `Idempotency-Key` but a different body returns HTTP 409. | `uv run pytest probes/test_probe.py -q -k test_idempotent_replay_different_body_conflicts 2>&1 \| tail -2` |

## Leg 3 — Transaction history and operator docs

| id | criterion | verification_command |
|---|---|---|
| AC-17 | `GET /accounts/{id}/transactions` returns HTTP 200 with `items` and `total` as top-level keys. | `curl -s http://localhost:8000/accounts/$(curl -s -X POST http://localhost:8000/accounts -H 'Content-Type: application/json' -d '{"name":"ac17"}' \| python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")/transactions \| python3 -c "import sys,json; d=json.load(sys.stdin); print(sorted(d.keys()))"` |
| AC-18 | `GET /accounts/{id}/transactions` for an unknown account returns HTTP 404. | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/accounts/00000000-0000-0000-0000-000000000000/transactions` |
| AC-19 | `GET /accounts/{id}/transactions` with no explicit `limit` returns at most 20 items; `total` reflects the count of all records, not the page size; results are ordered newest-first. | `uv run pytest probes/test_probe.py -q -k test_pagination_default_limit_and_ordering 2>&1 \| tail -2` |
| AC-20 | `GET /accounts/{id}/transactions?limit=101` returns HTTP 422. | `curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8000/accounts/00000000-0000-0000-0000-000000000000/transactions?limit=101'` |
| note | AC-20 uses a non-existent account id. FastAPI's Query parameter range check (`le=100`) fires before any database lookup, so the 422 response does not require a pre-existing account. | — |
| AC-21 | `GET /accounts/{id}/transactions?offset=<past-end>` returns HTTP 200 with an empty `items` list and the correct `total`. | `uv run pytest probes/test_probe.py -q -k test_pagination_offset_past_end 2>&1 \| tail -2` |
| AC-22 | `created_at` on a re-fetched account is timezone-aware, confirming the datetime survives the SQLite persistence round-trip without losing its UTC offset. | `uv run pytest probes/test_probe.py -q -k test_timestamps_are_timezone_aware_after_roundtrip 2>&1 \| tail -2` |
| AC-23 | `README.md` exists at the repository root. | `test -f README.md && echo present` |
| AC-24 | `README.md` contains `uv sync` in its quickstart instructions. | `python3 -c "t=open('README.md').read(); print('ok' if 'uv sync' in t else 'missing')"` |
| AC-25 | `README.md` contains `uvicorn app.main:app` (the command to run the API). | `python3 -c "t=open('README.md').read(); print('ok' if 'uvicorn app.main:app' in t else 'missing')"` |
| AC-26 | `README.md` endpoint table includes a `GET /accounts/{id}` entry. | `python3 -c "t=open('README.md').read(); print('ok' if 'GET /accounts' in t else 'missing')"` |
| AC-27 | `README.md` endpoint table includes a `POST /transfers` entry. | `python3 -c "t=open('README.md').read(); print('ok' if 'POST /transfers' in t else 'missing')"` |

---

## Family-M scoring inputs

The four scoring inputs that Stage 2 writes to `verdict.family_outcome` for M-relay runs:

### `verdict.family_outcome.final_outcome`

The L/S formula applied to the leg-3 repository:

```
final_outcome =
  (acceptance_share × 30 + gates_passed × 10 + probe_share × 10
   + max(0, 10 - 2 × confirmed_bugs)) / 60
```

where `acceptance_share = passed_items / 27`, `gates_passed ∈ {0, 1}`,
`probe_share = probes_passed / 12`.

### `verdict.family_outcome.continuity`

Share of the seven `continuity.md` rows that pass at the end of the run:

```
continuity = rows_passed / 7
```

The evaluator runs each verification command in `continuity.md` and counts passing rows.

### `verdict.family_outcome.rework_ratio`

Lines rewritten of already-delivered work, measured from git tags at each leg boundary.
The run harness creates a tag at the end of each leg:

- `m-relay-leg1`: tag placed at the HEAD commit when the solver finishes leg 1
- `m-relay-leg2`: tag placed at the HEAD commit when the solver finishes leg 2
- `m-relay-leg3`: tag placed at the final HEAD (equivalent to the evaluation commit)

**Numerator** (`lines_reworked`): lines that existed at the end of leg 1 that were removed
or replaced by the end of leg 3. This measures how much code written in leg 1 was later
changed:

```bash
git diff m-relay-leg1 m-relay-leg3 | grep '^-' | grep -v '^---' | wc -l
```

**Denominator** (`lines_delivered`): all new lines added from the scaffold baseline to the
final leg-3 commit:

```bash
git diff bench-base m-relay-leg3 | grep '^+' | grep -v '^+++' | wc -l
```

**Formula:**

```
rework_ratio = lines_reworked / lines_delivered
```

Both values are integers (line counts). `rework_ratio` is a real number in `[0, ∞)` but is
typically in `[0, 0.3]`; a value above 0.5 indicates the solver re-implemented significant
portions of leg-1 code. The evaluator clips at 1.0 for the scoring formula
(`0.2 × (1 − min(1, rework_ratio))`).

### `verdict.family_outcome.rediscovery_cost_usd` (reported only, not scored)

The cost the solver incurred to re-orient itself at the start of each continuation leg.
This is already captured by `telemetry.totals.cost_usd` and the per-role breakdown in
`telemetry.by_role`. Scoring it separately would double-count what is already in
`efficiency`. Report it as an informational line in the round report:

```
rediscovery_cost_usd = sum of input-token cost in the first N turns of legs 2 and 3
                       before the first tool write or code edit
```

The evaluator estimates this from the per-leg telemetry if the harness records per-leg
breakdowns; otherwise it is left as `null` and noted as unavailable.
