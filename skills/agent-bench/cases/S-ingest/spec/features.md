# Ingest: schema-validating CSV → Parquet CLI

A self-contained Python 3.12 command-line tool that reads a CSV file,
validates each row against a fixed schema, writes valid rows to a Parquet
output file, and quarantines invalid rows to a separate CSV with a reason
column. This file is the full contract; the governance roles review against
it verbatim.

**Stack (fixed — do not substitute):** `uv` project with committed `uv.lock`
and `.python-version` (3.12). Dependencies: `polars` for dataframe operations
and Parquet writes; dev group: `pytest`, `ruff`. No other runtime dependencies
are required.

**Entry point:** the `ingest` CLI registered in `[project.scripts]` in
`pyproject.toml`. Invoke as `uv run ingest` from the project root.

**Gates:** `uv run ruff check .` and `uv run pytest -q` must exit 0 after every
feature. Tests must be fully self-contained: use temporary files per test, no
network access, no external services, no ordering dependencies.

**Global rules:** every acceptance bullet below is a literal check — reviewers
walk them one by one. Existing behavior from earlier features must keep working
when later features land.

## CLI interface

```sh
ingest --input <path> --output <path> --quarantine <path> [--strict]
```

| Flag | Required | Description |
|---|---|---|
| `--input` | yes | Path to the input CSV file |
| `--output` | yes | Path to write the valid-rows Parquet file |
| `--quarantine` | yes | Path to write the invalid-rows CSV file |
| `--strict` | no | When set, exit code 2 if any rows were quarantined |

## Input schema

The input CSV must have exactly these four columns:

| Column | Validation rule |
|---|---|
| `id` | Non-empty string; unique within the file |
| `amount_minor` | Castable to a Python `int`; fractional values such as `"12.5"` are invalid |
| `currency` | Exactly three uppercase ASCII letters (`[A-Z]{3}`) |
| `occurred_at` | ISO-8601 datetime string with an explicit timezone offset (e.g. `2026-01-01T00:00:00+00:00`); a naive datetime without offset is invalid |

Rules are evaluated in the order listed above. When a row fails more than one
rule, the `reason` in the quarantine output names the **first** failing rule in
that order (`id` → `amount_minor` → `currency` → `occurred_at`).

## Processing contract

**Valid rows** are written to `--output` (Parquet format via polars)
preserving the order they appeared in the input CSV.

**Invalid rows** are written to `--quarantine` (CSV format) with all four
original columns plus a fifth column `reason`. The `reason` value is the name
of the first failing rule: `id`, `amount_minor`, `currency`, or `occurred_at`.

A **duplicate `id`** triggers the id uniqueness check: the first occurrence of
a given `id` proceeds to the remaining rule checks; each subsequent occurrence
with the same `id` is quarantined with `reason = id`. The id uniqueness check
applies to every id seen so far in the file, regardless of whether earlier
occurrences were valid or quarantined for other reasons.

## Exit codes

| Condition | Exit code |
|---|---|
| Input file does not exist | `2` |
| `--strict` is set and at least one row was quarantined | `2` |
| No rows are valid (including a header-only empty file) | `1` |
| At least one row is valid | `0` |

When more than one condition could apply, the higher-numbered code takes
precedence (`2` beats `1` beats `0`). In particular:

- `--strict` overrides the base valid/invalid determination: if `--strict` is
  set and any row was quarantined, the exit code is `2` regardless of whether
  valid rows also exist.
- A missing input file always exits `2`, regardless of `--strict`.
- `--strict` with no quarantined rows (all rows valid) exits `0`.

## Summary output

After processing (regardless of exit code), the tool prints exactly one line
to **stdout**:

```
read=<n> valid=<n> quarantined=<n>
```

Where `<n>` are non-negative integers. A missing input file is the only case
that skips this line (the error message goes to **stderr** only).

## Missing input file

When `--input` names a file that does not exist:

- Print a human-readable error message to **stderr**.
- Exit with code `2`.
- Create **no** output files (`--output` and `--quarantine` must not be created).

## Empty input file

An input file that contains only the header row and no data rows:

- Exits with code `1` (no valid rows).
- Writes an empty Parquet file to `--output` with the four-column schema:
  `id` (String/Utf8), `amount_minor` (Int64), `currency` (String/Utf8),
  `occurred_at` (String/Utf8).
- Writes an empty CSV file to `--quarantine` with the five-column header
  `id,amount_minor,currency,occurred_at,reason` and no data rows.
- Prints `read=0 valid=0 quarantined=0` to stdout.

## Operator docs

`README.md` at the repo root must contain:

- A quickstart section with `uv sync` and an example `uv run ingest` invocation.
- A table of the four input column names and their validation rules.
- The exit code table (conditions → codes).
