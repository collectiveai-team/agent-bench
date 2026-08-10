"""Black-box probe suite for the S-ledger benchmark case.

Exercises the public HTTP surface. Makes no assumptions about the solver's
internal module layout; `app.main.create_app` is the only imported name from
the solver's package (the public ASGI entry point that spec/features.md
requires). The fixture evicts all `app.*` modules from `sys.modules` rather
than importing a specific settings path, so no internal structure is assumed.

Uses an in-process ASGI transport (starlette.testclient.TestClient) — no live
server is required or started.

Run from the solver's repository root:  uv run pytest probes/test_probe.py -q

Test 12 (test_timestamps_are_timezone_aware_after_roundtrip) exists because a
naive-datetime round-trip loss was a recurrent defect in prior benchmark rounds:
an implementation may serialize an aware datetime on the creation response while
the persistence layer stores it naively, so the creation response passes but a
re-fetch fails. The test re-fetches the record to exercise the storage path.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.getcwd())  # probe runs from the solver's repo root


# ── fixture ────────────────────────────────────────────────────────────────────


def _purge_app_modules() -> None:
    """Evict the entire app package from sys.modules so the next import
    re-reads env vars into a fresh Settings instance.

    Removes all 'app' and 'app.*' entries rather than importing a specific
    module path, making no structural assumptions about the solver's layout.
    """
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]


@pytest.fixture()
def client(tmp_path):
    """A TestClient backed by a brand-new app instance using a throwaway SQLite file."""
    os.environ["LEDGER_DB_PATH"] = str(tmp_path / "ledger.db")
    _purge_app_modules()
    from app.main import create_app  # noqa: PLC0415

    with TestClient(create_app()) as c:
        yield c


# ── helpers ────────────────────────────────────────────────────────────────────


def _make_account(client: TestClient, name: str = "test") -> dict:
    r = client.post("/accounts", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


def _credit(client: TestClient, account_id: str, amount: int) -> dict:
    r = client.post(f"/accounts/{account_id}/credit", json={"amount_minor": amount})
    assert r.status_code == 201, r.text
    return r.json()


def _transfer(
    client: TestClient,
    from_id: str,
    to_id: str,
    amount: int,
    key: str | None = None,
) -> tuple[int, dict]:
    headers = {"Idempotency-Key": key or str(uuid.uuid4())}
    r = client.post(
        "/transfers",
        json={"from_account_id": from_id, "to_account_id": to_id, "amount_minor": amount},
        headers=headers,
    )
    return r.status_code, r.json()


def _balance(client: TestClient, account_id: str) -> int:
    r = client.get(f"/accounts/{account_id}")
    assert r.status_code == 200, r.text
    return r.json()["balance_minor"]


# ── tests ──────────────────────────────────────────────────────────────────────


def test_credit_then_balance(client):
    """Credit 500 minor units; re-fetching the account shows balance_minor == 500."""
    acct = _make_account(client)
    _credit(client, acct["id"], 500)
    assert _balance(client, acct["id"]) == 500


def test_transfer_moves_exact_minor_units(client):
    """After a 250-unit transfer the source holds 250 and the destination holds 250; values must be ints, not floats."""
    src = _make_account(client, "src")
    dst = _make_account(client, "dst")
    _credit(client, src["id"], 500)
    status, body = _transfer(client, src["id"], dst["id"], 250)
    assert status == 201, body
    src_bal = _balance(client, src["id"])
    dst_bal = _balance(client, dst["id"])
    assert src_bal == 250
    assert dst_bal == 250
    # values must be plain integers (not floats, not booleans)
    assert isinstance(src_bal, int) and not isinstance(src_bal, bool)
    assert isinstance(dst_bal, int) and not isinstance(dst_bal, bool)
    # response body amount_minor is also an integer
    assert isinstance(body["amount_minor"], int) and not isinstance(body["amount_minor"], bool)


def test_transfer_records_transaction_rows(client):
    """A successful transfer appends one debit transaction (-amount_minor) to the source and one credit transaction (+amount_minor) to the destination."""
    src = _make_account(client, "src")
    dst = _make_account(client, "dst")
    _credit(client, src["id"], 500)  # one credit transaction on src
    _transfer(client, src["id"], dst["id"], 300)

    src_txns = client.get(f"/accounts/{src['id']}/transactions").json()
    dst_txns = client.get(f"/accounts/{dst['id']}/transactions").json()

    # source: one credit (from _credit above) + one debit (from transfer) = 2 total
    assert src_txns["total"] == 2, f"expected 2 transactions on source, got {src_txns['total']}"
    # newest-first: the debit appears first
    assert src_txns["items"][0]["amount_minor"] == -300, (
        f"expected debit of -300 as newest source transaction, "
        f"got {src_txns['items'][0]['amount_minor']}"
    )
    # destination: one credit from the transfer = 1 total
    assert dst_txns["total"] == 1, f"expected 1 transaction on destination, got {dst_txns['total']}"
    assert dst_txns["items"][0]["amount_minor"] == 300, (
        f"expected credit of 300 as destination transaction, "
        f"got {dst_txns['items'][0]['amount_minor']}"
    )


def test_idempotent_replay_same_body_returns_same_id_and_moves_once(client):
    """Two identical POST /transfers with the same Idempotency-Key: second returns 200 with the same id; balances do not change a second time."""
    src = _make_account(client, "src")
    dst = _make_account(client, "dst")
    _credit(client, src["id"], 1000)
    key = str(uuid.uuid4())
    status1, body1 = _transfer(client, src["id"], dst["id"], 100, key=key)
    assert status1 == 201
    src_after_first = _balance(client, src["id"])
    dst_after_first = _balance(client, dst["id"])
    # replay with the same key and same body
    status2, body2 = _transfer(client, src["id"], dst["id"], 100, key=key)
    assert status2 == 200, f"expected 200 on replay, got {status2}: {body2}"
    assert body2["id"] == body1["id"], "replay must return the same transfer id"
    assert _balance(client, src["id"]) == src_after_first, "replay must not debit source again"
    assert _balance(client, dst["id"]) == dst_after_first, "replay must not credit destination again"


def test_idempotent_replay_different_body_conflicts(client):
    """Same Idempotency-Key with a changed amount_minor returns 409."""
    src = _make_account(client, "src")
    dst = _make_account(client, "dst")
    _credit(client, src["id"], 2000)
    key = str(uuid.uuid4())
    status1, _ = _transfer(client, src["id"], dst["id"], 100, key=key)
    assert status1 == 201
    # same key, different amount — must conflict
    r = client.post(
        "/transfers",
        json={"from_account_id": src["id"], "to_account_id": dst["id"], "amount_minor": 200},
        headers={"Idempotency-Key": key},
    )
    assert r.status_code == 409


def test_missing_idempotency_key_rejected(client):
    """POST /transfers without an Idempotency-Key header returns 400."""
    src = _make_account(client, "src")
    dst = _make_account(client, "dst")
    _credit(client, src["id"], 500)
    r = client.post(
        "/transfers",
        json={"from_account_id": src["id"], "to_account_id": dst["id"], "amount_minor": 100},
    )
    assert r.status_code == 400


def test_non_positive_amount_rejected(client):
    """amount_minor == 0 and amount_minor == -1 both return 422 from POST /transfers."""
    src = _make_account(client, "src")
    dst = _make_account(client, "dst")
    for amount in (0, -1):
        r = client.post(
            "/transfers",
            json={
                "from_account_id": src["id"],
                "to_account_id": dst["id"],
                "amount_minor": amount,
            },
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        assert r.status_code == 422, f"expected 422 for amount_minor={amount}, got {r.status_code}"


def test_insufficient_funds(client):
    """Transfer more than available balance returns 409 with detail == 'insufficient_funds'; both balances are unchanged."""
    src = _make_account(client, "src")
    dst = _make_account(client, "dst")
    _credit(client, src["id"], 100)
    r = client.post(
        "/transfers",
        json={"from_account_id": src["id"], "to_account_id": dst["id"], "amount_minor": 200},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 409
    assert r.json().get("detail") == "insufficient_funds"
    assert _balance(client, src["id"]) == 100, "source balance must be unchanged after failed transfer"
    assert _balance(client, dst["id"]) == 0, "destination balance must be unchanged after failed transfer"


def test_unknown_account(client):
    """POST /transfers with an unknown from_account_id or to_account_id returns 404."""
    real = _make_account(client)
    _credit(client, real["id"], 500)
    ghost = str(uuid.uuid4())
    # unknown source
    r1 = client.post(
        "/transfers",
        json={"from_account_id": ghost, "to_account_id": real["id"], "amount_minor": 50},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r1.status_code == 404
    # unknown destination
    r2 = client.post(
        "/transfers",
        json={"from_account_id": real["id"], "to_account_id": ghost, "amount_minor": 50},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r2.status_code == 404


def test_pagination_default_limit_and_ordering(client):
    """25 credits to one account: default limit returns exactly 20 items; total is 25; results are ordered newest-first."""
    acct = _make_account(client)
    for _ in range(25):
        _credit(client, acct["id"], 10)

    r = client.get(f"/accounts/{acct['id']}/transactions")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 25, f"expected total 25, got {body['total']}"
    assert len(body["items"]) == 20, f"expected 20 items with default limit, got {len(body['items'])}"

    times = [item["created_at"] for item in body["items"]]
    assert times == sorted(times, reverse=True), "transactions must be ordered newest-first"


def test_pagination_offset_past_end(client):
    """Requesting an offset past the last record returns an empty items list with the correct total."""
    acct = _make_account(client)
    for _ in range(5):
        _credit(client, acct["id"], 10)

    r = client.get(f"/accounts/{acct['id']}/transactions?offset=10")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == [], f"expected empty items list, got {body['items']}"
    assert body["total"] == 5, f"expected total 5 (unchanged by offset), got {body['total']}"


def test_timestamps_are_timezone_aware_after_roundtrip(client):
    """created_at on a re-fetched account is timezone-aware, proving the value survives the persistence round-trip.

    This test exists because a naive-datetime round-trip loss recurred across
    independent implementations in prior rounds: the creation response may
    return an aware datetime built in Python memory while the value stored in
    SQLite is naive. Re-fetching forces the storage path to exercise.
    """
    acct = _make_account(client)
    # re-fetch — exercises the persistence round-trip, not the creation response
    r = client.get(f"/accounts/{acct['id']}")
    assert r.status_code == 200
    fetched = r.json()
    dt = datetime.fromisoformat(fetched["created_at"])
    assert dt.tzinfo is not None, (
        f"created_at is naive after persistence round-trip: {fetched['created_at']!r}"
    )
