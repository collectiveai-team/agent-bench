# Continuity checklist — M-relay

**This file is evaluation material. A solver must never see it.**

Stage 2 of the evaluator runs the verification commands below against the completed leg-3
repository (server running on `http://localhost:8000`) after all three sessions have finished.
Each row is one leg-1 design decision that legs 2 and 3 must honour. The `continuity` score
is `rows_passed / total_rows` (seven rows).

The live server is started by the evaluator with:
```sh
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

| id | decision | verification_command | expected_output |
|---|---|---|---|
| CC-01 | `balance_minor` is an integer (not float, not bool) throughout the money path; a newly created account returns an integer 0, not 0.0 or False. | `curl -s -X POST http://localhost:8000/accounts -H 'Content-Type: application/json' -d '{"name":"cc01"}' \| python3 -c "import sys,json; d=json.load(sys.stdin); v=d.get('balance_minor'); print('int' if isinstance(v,int) and not isinstance(v,bool) else 'not-int')"` | `int` |
| CC-02 | Account `id` is a version-4 UUID string (8-4-4-4-12 hex, version digit 4, variant bits 8/9/a/b). | `curl -s -X POST http://localhost:8000/accounts -H 'Content-Type: application/json' -d '{"name":"cc02"}' \| python3 -c "import sys,json,re; d=json.load(sys.stdin); uid=d.get('id',''); print('uuid4' if re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',uid,re.I) else 'not-uuid4')"` | `uuid4` |
| CC-03 | The 404 error body for an unknown account is `{"detail": "account not found"}` — the exact `detail` key and exact string value. | `curl -s http://localhost:8000/accounts/00000000-0000-0000-0000-000000000000 \| python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail'))"` | `account not found` |
| CC-04 | `created_at` on a newly created account is UTC-aware (contains `+` or ends with `Z`). | `curl -s -X POST http://localhost:8000/accounts -H 'Content-Type: application/json' -d '{"name":"cc04"}' \| python3 -c "import sys,json; d=json.load(sys.stdin); ts=d.get('created_at',''); print('aware' if ('+' in ts or ts.endswith('Z')) else 'naive')"` | `aware` |
| CC-05 | `created_at` survives the SQLite persistence round-trip: a re-fetched account has a timezone-aware `created_at`, not a naive string. | `python3 -c "import urllib.request,json,datetime; r=urllib.request.urlopen('http://localhost:8000/accounts',data=b'{\"name\":\"cc05\"}',method='POST'); acct=json.loads(r.read()); uid=acct['id']; r2=urllib.request.urlopen(f'http://localhost:8000/accounts/{uid}'); d2=json.loads(r2.read()); ts=d2['created_at']; print('aware' if ('+' in ts or ts.endswith('Z')) else 'naive')"` | `aware` |
| CC-06 | The 404 error body for an unknown account is identical when raised by a transfer endpoint (`POST /transfers` with an unknown `from_account_id`) — same `detail` value, same key. | `curl -s -X POST http://localhost:8000/transfers -H 'Content-Type: application/json' -H 'Idempotency-Key: cc06' -d '{"from_account_id":"00000000-0000-0000-0000-000000000000","to_account_id":"00000000-0000-0000-0000-000000000001","amount_minor":50}' \| python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail'))"` | `account not found` |
| CC-07 | No leg-1 endpoint contract is altered: `POST /accounts` still returns 201 and `GET /accounts/{id}` still returns 200 with `balance_minor` as a key. | `python3 -c "import urllib.request,json; r=urllib.request.urlopen('http://localhost:8000/accounts',data=b'{\"name\":\"cc07\"}',method='POST'); acct=json.loads(r.read()); uid=acct['id']; r2=urllib.request.urlopen(f'http://localhost:8000/accounts/{uid}'); d=json.loads(r2.read()); print('ok' if 'balance_minor' in d else 'missing')"` | `ok` |

---

## Scoring

`continuity = rows_passed / 7`

The score is written by Stage 2 to `verdict.family_outcome.continuity`. Each row is
independently verifiable; a partial score is valid.
