"""Black-box probe suite for the S-ingest benchmark case.

Exercises the CLI's public surface: exit codes, stdout, stderr, and the
contents of the output Parquet and quarantine CSV files. The CLI is invoked
as a subprocess via `uv run ingest`; no internal modules are imported.

Run from the solver's repository root:  uv run pytest probes/test_probe.py -q
"""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import polars as pl
import pytest

CLI = ["uv", "run", "ingest"]


# ── helpers ────────────────────────────────────────────────────────────────────


def _run(
    input_path: str | Path,
    output_path: str | Path,
    quarantine_path: str | Path,
    strict: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        *CLI,
        "--input", str(input_path),
        "--output", str(output_path),
        "--quarantine", str(quarantine_path),
    ]
    if strict:
        cmd.append("--strict")
    return subprocess.run(cmd, capture_output=True, text=True)


def _write_csv(path: Path, rows: list[dict]) -> None:
    """Write rows to a CSV; if rows is empty, write only the header."""
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "amount_minor", "currency", "occurred_at"]
        )
        writer.writeheader()
        writer.writerows(rows)


VALID_ROWS = [
    {
        "id": "row1",
        "amount_minor": "100",
        "currency": "USD",
        "occurred_at": "2026-01-01T00:00:00+00:00",
    },
    {
        "id": "row2",
        "amount_minor": "200",
        "currency": "EUR",
        "occurred_at": "2026-06-15T12:30:00+05:30",
    },
    {
        "id": "row3",
        "amount_minor": "50",
        "currency": "GBP",
        "occurred_at": "2026-12-31T23:59:59-05:00",
    },
]


# ── tests ──────────────────────────────────────────────────────────────────────


def test_all_valid_rows_pass_through_in_order(tmp_path):
    """All valid rows appear in the Parquet output in input order; quarantine has
    only its header; exit code is 0; stdout summary is read=3 valid=3 quarantined=0.
    Also checks that amount_minor is stored as Int64 in the Parquet schema."""
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.parquet"
    quar = tmp_path / "quar.csv"
    _write_csv(inp, VALID_ROWS)

    result = _run(inp, out, quar)

    assert result.returncode == 0
    assert result.stdout.strip() == "read=3 valid=3 quarantined=0"

    df = pl.read_parquet(out)
    assert len(df) == 3
    assert df["id"].to_list() == ["row1", "row2", "row3"], "input order must be preserved"
    assert df["amount_minor"].dtype == pl.Int64, "amount_minor must be Int64 in the Parquet schema"

    with quar.open() as f:
        reader = csv.reader(f)
        header = next(reader)
        data_rows = list(reader)
    assert header == ["id", "amount_minor", "currency", "occurred_at", "reason"]
    assert data_rows == [], "quarantine must be empty when all rows are valid"


def test_bad_amount_quarantined_with_reason(tmp_path):
    """Rows with non-integer amount_minor (float string and non-numeric string) are
    quarantined with reason 'amount_minor'; the valid row reaches the Parquet output."""
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.parquet"
    quar = tmp_path / "quar.csv"
    _write_csv(inp, [
        {"id": "good", "amount_minor": "100", "currency": "USD",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
        {"id": "bad_float", "amount_minor": "12.5", "currency": "USD",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
        {"id": "bad_str", "amount_minor": "notanint", "currency": "EUR",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
    ])

    result = _run(inp, out, quar)

    assert result.returncode == 0
    assert result.stdout.strip() == "read=3 valid=1 quarantined=2"

    df = pl.read_parquet(out)
    assert len(df) == 1
    assert df["id"].to_list() == ["good"]

    with quar.open() as f:
        reader = csv.DictReader(f)
        bad_rows = list(reader)
    assert len(bad_rows) == 2
    assert all(r["reason"] == "amount_minor" for r in bad_rows), (
        f"expected reason='amount_minor' for all bad rows, got: {[r['reason'] for r in bad_rows]}"
    )
    bad_ids = {r["id"] for r in bad_rows}
    assert bad_ids == {"bad_float", "bad_str"}
    # original columns must be present in quarantine
    assert all("id" in r and "currency" in r and "occurred_at" in r for r in bad_rows)


def test_bad_currency_quarantined_with_reason(tmp_path):
    """Lowercase three-letter and four-letter currency codes are both quarantined
    with reason 'currency'; a valid three-letter uppercase code passes through."""
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.parquet"
    quar = tmp_path / "quar.csv"
    _write_csv(inp, [
        {"id": "good", "amount_minor": "100", "currency": "USD",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
        {"id": "lower", "amount_minor": "100", "currency": "usd",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
        {"id": "four", "amount_minor": "100", "currency": "USDD",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
    ])

    result = _run(inp, out, quar)

    assert result.returncode == 0
    assert result.stdout.strip() == "read=3 valid=1 quarantined=2"

    with quar.open() as f:
        reader = csv.DictReader(f)
        bad_rows = list(reader)
    assert len(bad_rows) == 2
    assert all(r["reason"] == "currency" for r in bad_rows), (
        f"expected reason='currency' for all bad rows, got: {[r['reason'] for r in bad_rows]}"
    )
    bad_ids = {r["id"] for r in bad_rows}
    assert bad_ids == {"lower", "four"}


def test_naive_timestamp_quarantined(tmp_path):
    """A timestamp without a timezone offset is quarantined with reason 'occurred_at'."""
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.parquet"
    quar = tmp_path / "quar.csv"
    _write_csv(inp, [
        {"id": "good", "amount_minor": "100", "currency": "USD",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
        {"id": "naive", "amount_minor": "100", "currency": "USD",
         "occurred_at": "2026-01-01T00:00:00"},
    ])

    result = _run(inp, out, quar)

    assert result.returncode == 0
    assert result.stdout.strip() == "read=2 valid=1 quarantined=1"

    with quar.open() as f:
        reader = csv.DictReader(f)
        bad_rows = list(reader)
    assert len(bad_rows) == 1
    assert bad_rows[0]["id"] == "naive"
    assert bad_rows[0]["reason"] == "occurred_at"


def test_duplicate_id_quarantines_the_later_row(tmp_path):
    """When two rows share an id, the first occurrence is kept and the later
    occurrence is quarantined with reason 'id'; the quarantine row carries
    the original column values from the later occurrence."""
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.parquet"
    quar = tmp_path / "quar.csv"
    _write_csv(inp, [
        {"id": "dup", "amount_minor": "100", "currency": "USD",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
        {"id": "unique", "amount_minor": "200", "currency": "EUR",
         "occurred_at": "2026-01-02T00:00:00+00:00"},
        {"id": "dup", "amount_minor": "300", "currency": "GBP",
         "occurred_at": "2026-01-03T00:00:00+00:00"},
    ])

    result = _run(inp, out, quar)

    assert result.returncode == 0
    assert result.stdout.strip() == "read=3 valid=2 quarantined=1"

    df = pl.read_parquet(out)
    assert len(df) == 2
    assert df["id"].to_list() == ["dup", "unique"], (
        "first occurrence of 'dup' and 'unique' must be in parquet, in input order"
    )

    with quar.open() as f:
        reader = csv.DictReader(f)
        bad_rows = list(reader)
    assert len(bad_rows) == 1
    assert bad_rows[0]["id"] == "dup"
    assert bad_rows[0]["reason"] == "id"
    # quarantined row carries values from the LATER occurrence
    assert bad_rows[0]["amount_minor"] == "300", (
        "quarantine must carry the later row's amount_minor (300), not the first (100)"
    )


def test_first_failing_rule_wins(tmp_path):
    """When a row fails multiple rules, the reason names the first failing rule
    in spec order: id → amount_minor → currency → occurred_at.

    Row 1: empty id AND invalid currency (lowercase) → reason must be 'id'.
    Row 2: valid id, non-integer amount AND invalid currency → reason must be 'amount_minor'.
    """
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.parquet"
    quar = tmp_path / "quar.csv"
    _write_csv(inp, [
        # empty id AND invalid currency: id is first in spec order → reason=id
        {"id": "", "amount_minor": "100", "currency": "usd",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
        # valid id, bad amount AND invalid currency: amount_minor before currency → reason=amount_minor
        {"id": "bad2", "amount_minor": "notanint", "currency": "usd",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
    ])

    result = _run(inp, out, quar)

    assert result.returncode == 1  # no valid rows

    with quar.open() as f:
        reader = csv.DictReader(f)
        bad_rows = list(reader)
    assert len(bad_rows) == 2
    reasons = {r["id"]: r["reason"] for r in bad_rows}
    assert reasons[""] == "id", (
        f"empty-id row with also-bad currency must report reason='id', got '{reasons.get('')}'"
    )
    assert reasons["bad2"] == "amount_minor", (
        f"row with bad amount AND bad currency must report reason='amount_minor', "
        f"got '{reasons.get('bad2')}'"
    )


def test_exit_codes(tmp_path):
    """Exit codes: 0 when any valid; 1 when none valid; 2 when --strict and any
    quarantined (overrides 0 and 1); 0 when --strict but no quarantined rows;
    1 for a header-only file with --strict (zero quarantined, zero valid → higher
    of 'none-valid → 1' and 'strict-no-quarantine → 0' is 1)."""
    valid_row = {
        "id": "v1", "amount_minor": "100", "currency": "USD",
        "occurred_at": "2026-01-01T00:00:00+00:00",
    }
    invalid_row = {
        "id": "x1", "amount_minor": "bad", "currency": "USD",
        "occurred_at": "2026-01-01T00:00:00+00:00",
    }

    # --- exit 0: at least one valid row ---
    inp = tmp_path / "all_valid.csv"
    _write_csv(inp, [valid_row])
    r = _run(inp, tmp_path / "out0.parquet", tmp_path / "q0.csv")
    assert r.returncode == 0, f"expected 0 when all rows valid, got {r.returncode}"

    # --- exit 1: no valid rows ---
    inp = tmp_path / "all_invalid.csv"
    _write_csv(inp, [invalid_row])
    r = _run(inp, tmp_path / "out1.parquet", tmp_path / "q1.csv")
    assert r.returncode == 1, f"expected 1 when no rows valid, got {r.returncode}"

    # --- exit 2: --strict with quarantined rows (mix of valid + invalid) ---
    inp = tmp_path / "mix.csv"
    _write_csv(inp, [valid_row, invalid_row])
    r = _run(inp, tmp_path / "out2.parquet", tmp_path / "q2.csv", strict=True)
    assert r.returncode == 2, f"expected 2 with --strict and quarantined, got {r.returncode}"

    # --- exit 0: --strict but no quarantined rows ---
    inp = tmp_path / "all_valid_strict.csv"
    _write_csv(inp, [valid_row])
    r = _run(inp, tmp_path / "out0s.parquet", tmp_path / "q0s.csv", strict=True)
    assert r.returncode == 0, (
        f"expected 0 with --strict but no quarantined rows, got {r.returncode}"
    )

    # --- exit 1: header-only file with --strict ---
    # zero quarantined rows and zero valid rows: "no valid rows → 1" wins over
    # "strict with nothing quarantined → 0"; precedence: 2 > 1 > 0.
    inp = tmp_path / "empty_strict.csv"
    inp.write_text("id,amount_minor,currency,occurred_at\n")
    r = _run(inp, tmp_path / "out_es.parquet", tmp_path / "q_es.csv", strict=True)
    assert r.returncode == 1, (
        f"expected 1 for header-only file with --strict (no-valid beats strict-no-quarantine), "
        f"got {r.returncode}"
    )


def test_missing_and_empty_input(tmp_path):
    """Missing input file: exit 2, stderr message, no output files created, no stdout.
    Header-only file: exit 1, empty Parquet with correct schema, empty
    quarantine CSV with five-column header, stdout summary read=0 valid=0 quarantined=0."""
    # --- missing input file ---
    missing = tmp_path / "does_not_exist.csv"
    out = tmp_path / "out.parquet"
    quar = tmp_path / "quar.csv"
    r = _run(missing, out, quar)
    assert r.returncode == 2, f"expected 2 for missing input file, got {r.returncode}"
    assert r.stderr.strip() != "", "expected an error message on stderr for missing input file"
    assert r.stdout.strip() == "", (
        f"missing input file must print nothing to stdout (error goes to stderr only), "
        f"got: {r.stdout!r}"
    )
    assert not out.exists(), "output Parquet must not be created when input is missing"
    assert not quar.exists(), "quarantine CSV must not be created when input is missing"

    # --- header-only (empty) input file ---
    empty_inp = tmp_path / "empty.csv"
    empty_inp.write_text("id,amount_minor,currency,occurred_at\n")
    out2 = tmp_path / "out2.parquet"
    quar2 = tmp_path / "quar2.csv"
    r2 = _run(empty_inp, out2, quar2)
    assert r2.returncode == 1, f"expected 1 for header-only file, got {r2.returncode}"
    assert r2.stdout.strip() == "read=0 valid=0 quarantined=0"

    # empty Parquet has correct four-column schema
    df = pl.read_parquet(out2)
    assert len(df) == 0
    assert set(df.columns) == {"id", "amount_minor", "currency", "occurred_at"}
    assert df["amount_minor"].dtype == pl.Int64, (
        "amount_minor column must be Int64 even in the empty Parquet"
    )

    # empty quarantine CSV has correct five-column header
    with quar2.open() as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows[0] == ["id", "amount_minor", "currency", "occurred_at", "reason"], (
        f"quarantine header must be exactly the five expected columns, got: {rows[0]}"
    )
    assert len(rows) == 1, "quarantine CSV for empty input must have only the header row"


def test_duplicate_id_when_first_occurrence_quarantined(tmp_path):
    """The id uniqueness check applies to ALL ids seen so far, regardless of whether
    the first occurrence was quarantined for a different reason.

    Row A: id='X', bad amount_minor → quarantined with reason='amount_minor'; id 'X' is now seen.
    Row B: id='X', all fields valid → must be quarantined with reason='id' (duplicate),
           not written to the Parquet output.

    A solver that only tracks ids of valid rows would pass Row B through to the Parquet,
    violating the spec clause 'unique within the file'.
    """
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.parquet"
    quar = tmp_path / "quar.csv"
    _write_csv(inp, [
        # Row A: id='X', bad amount → quarantined for amount_minor; but 'X' enters seen_ids
        {"id": "X", "amount_minor": "notanint", "currency": "USD",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
        # Row B: id='X', all valid → must be quarantined as duplicate (reason='id')
        {"id": "X", "amount_minor": "100", "currency": "USD",
         "occurred_at": "2026-01-01T00:00:00+00:00"},
        # Row C: unique valid row → should reach the Parquet output
        {"id": "Y", "amount_minor": "200", "currency": "EUR",
         "occurred_at": "2026-01-02T00:00:00+00:00"},
    ])

    result = _run(inp, out, quar)

    assert result.returncode == 0  # Row C is valid
    assert result.stdout.strip() == "read=3 valid=1 quarantined=2"

    df = pl.read_parquet(out)
    assert len(df) == 1
    assert df["id"].to_list() == ["Y"], (
        "only Row C (id='Y') must be in the Parquet; Row B must be quarantined as duplicate"
    )

    with quar.open() as f:
        reader = csv.DictReader(f)
        bad_rows = list(reader)
    assert len(bad_rows) == 2
    reasons_by_id = {r["id"]: r["reason"] for r in bad_rows}
    assert reasons_by_id["X"] == "amount_minor" or reasons_by_id.get("X") == "id", (
        "Row A must be quarantined (either for amount_minor on first occurrence or id on second)"
    )
    # The critical assertion: the SECOND occurrence of 'X' must be quarantined as 'id'
    # Collect all reasons for rows with id='X'
    x_reasons = [r["reason"] for r in bad_rows if r["id"] == "X"]
    assert "id" in x_reasons, (
        f"the second occurrence of id='X' (with valid data) must be quarantined with reason='id', "
        f"but got reasons for 'X': {x_reasons}"
    )
