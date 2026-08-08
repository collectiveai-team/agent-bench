# Acceptance criteria — S-ingest

Frozen item count: **22**

Each row is one observable criterion. The evaluator runs `verification_command`
verbatim in the root of a fresh clone of the solver's branch and determines
pass/fail from the observed output alone.

All inline commands use `uv run ingest` (via subprocess) to invoke the CLI.
The evaluator's pre-flight (Step 3: `uv run pytest -q`) has already exercised
the venv, so `uv run ingest` is available without an extra sync step.

Items whose `verification_command` runs `uv run pytest probes/test_probe.py ...`
rely on the probe file having been copied to `probes/test_probe.py` at the clone
root by Stage 2 Step 4. These probe-as-acceptance items are used where no single
stateless shell command can observe the criterion (parquet column dtypes and row
values, quarantine row fidelity, input-order preservation). An acceptance item
that is a probe test moves both `acceptance_share × 30` and `probe_share × 10`
in the scoring formula — those two terms are not fully independent for items
AC-02, AC-04, AC-07, AC-08, and AC-19. All other items are independent of the
probe scores.

**Granularity note for AC-05/AC-06:** Lowercase-currency and four-letter-currency
are tested with separate inline commands because they are independently falsifiable:
a solver implementing only a length check would pass AC-06 (four-letter "USDD"
caught) but fail AC-06 if they only check for uppercase — actually each tests a
different constraint of the `[A-Z]{3}` rule, so a one-sided implementation can
fail one without failing the other.

**Granularity note for AC-09/AC-10:** These replace a single probe-as-acceptance
row because empty-id detection (AC-09) and rule-ordering (AC-10) are independently
falsifiable. A solver that checks rule order correctly but does not quarantine
empty ids would fail AC-09 and pass AC-10; a solver that quarantines empty ids
but applies rules in the wrong order would fail AC-10 and pass AC-09.

| id | criterion | verification_command |
|---|---|---|
| AC-01 | Running `uv run ingest --help` exits 0. | `uv run ingest --help > /dev/null 2>&1 && echo ok` |
| AC-02 | Valid rows are written to the Parquet output in the order they appeared in the input CSV; `amount_minor` has dtype Int64 in the Parquet schema; the quarantine output has only its header when all rows are valid. | `uv run pytest probes/test_probe.py -q -k test_all_valid_rows_pass_through_in_order 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-03 | After processing three valid rows, stdout is exactly `read=3 valid=3 quarantined=0`. | `python3 -c "import subprocess,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'i.csv').write_text('id,amount_minor,currency,occurred_at\nr1,100,USD,2026-01-01T00:00:00+00:00\nr2,200,EUR,2026-06-15T12:30:00+05:30\nr3,50,GBP,2026-12-31T23:59:59-05:00\n');r=subprocess.run(['uv','run','ingest','--input',str(d/'i.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True,text=True);print(r.stdout.strip())"` |
| note | Expected output: `read=3 valid=3 quarantined=0`. | — |
| AC-04 | A row with a non-integer `amount_minor` (e.g. `"12.5"`) is quarantined with `reason=amount_minor`; the original columns are preserved in the quarantine row. | `uv run pytest probes/test_probe.py -q -k test_bad_amount_quarantined_with_reason 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-05 | A row with a lowercase three-letter currency code (e.g. `"usd"`) is quarantined with `reason=currency`. | `python3 -c "import subprocess,csv,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'i.csv').write_text('id,amount_minor,currency,occurred_at\nbad,100,usd,2026-01-01T00:00:00+00:00\n');subprocess.run(['uv','run','ingest','--input',str(d/'i.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);rows=list(csv.DictReader((d/'q.csv').open()));print(rows[0]['reason'] if rows else 'empty')"` |
| note | Expected output: `currency`. | — |
| AC-06 | A row with a four-letter currency code (e.g. `"USDD"`) is quarantined with `reason=currency`. | `python3 -c "import subprocess,csv,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'i.csv').write_text('id,amount_minor,currency,occurred_at\nbad,100,USDD,2026-01-01T00:00:00+00:00\n');subprocess.run(['uv','run','ingest','--input',str(d/'i.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);rows=list(csv.DictReader((d/'q.csv').open()));print(rows[0]['reason'] if rows else 'empty')"` |
| note | Expected output: `currency`. | — |
| AC-07 | A row with a timezone-naive `occurred_at` (no offset) is quarantined with `reason=occurred_at`. | `uv run pytest probes/test_probe.py -q -k test_naive_timestamp_quarantined 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-08 | When two rows share an `id`, the first occurrence is in the Parquet output, the later occurrence is quarantined with `reason=id`, and the quarantine row carries the original column values from the later occurrence. | `uv run pytest probes/test_probe.py -q -k test_duplicate_id_quarantines_the_later_row 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-09 | A row with an empty `id` string is quarantined with `reason=id`. | `python3 -c "import subprocess,csv,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'i.csv').write_text('id,amount_minor,currency,occurred_at\n,100,USD,2026-01-01T00:00:00+00:00\n');subprocess.run(['uv','run','ingest','--input',str(d/'i.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);rows=list(csv.DictReader((d/'q.csv').open()));print(rows[0]['reason'] if rows else 'empty')"` |
| note | Expected output: `id`. | — |
| AC-10 | A row with a non-integer `amount_minor` AND an invalid `currency` reports `reason=amount_minor` (the first failing rule in spec order). | `python3 -c "import subprocess,csv,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'i.csv').write_text('id,amount_minor,currency,occurred_at\nbad2,notanint,usd,2026-01-01T00:00:00+00:00\n');subprocess.run(['uv','run','ingest','--input',str(d/'i.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);rows=list(csv.DictReader((d/'q.csv').open()));print(rows[0]['reason'] if rows else 'empty')"` |
| note | Expected output: `amount_minor`. A result of `currency` means the solver evaluated currency before amount_minor, violating the spec-mandated rule order. | — |
| AC-11 | The quarantine CSV contains the original four input columns plus a fifth `reason` column. | `python3 -c "import subprocess,csv,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'i.csv').write_text('id,amount_minor,currency,occurred_at\nbad,notanint,USD,2026-01-01T00:00:00+00:00\n');subprocess.run(['uv','run','ingest','--input',str(d/'i.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);print(list(csv.DictReader((d/'q.csv').open()).fieldnames))"` |
| note | Expected output: `['id', 'amount_minor', 'currency', 'occurred_at', 'reason']`. | — |
| AC-12 | Exit code is `0` when at least one row is valid. | `python3 -c "import subprocess,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'i.csv').write_text('id,amount_minor,currency,occurred_at\nr1,100,USD,2026-01-01T00:00:00+00:00\n');r=subprocess.run(['uv','run','ingest','--input',str(d/'i.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);print(r.returncode)"` |
| note | Expected output: `0`. | — |
| AC-13 | Exit code is `1` when no rows are valid. | `python3 -c "import subprocess,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'i.csv').write_text('id,amount_minor,currency,occurred_at\nbad,notanint,USD,2026-01-01T00:00:00+00:00\n');r=subprocess.run(['uv','run','ingest','--input',str(d/'i.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);print(r.returncode)"` |
| note | Expected output: `1`. | — |
| AC-14 | Exit code is `2` when `--strict` is set and at least one row was quarantined (even if valid rows also exist). | `python3 -c "import subprocess,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'i.csv').write_text('id,amount_minor,currency,occurred_at\ngood,100,USD,2026-01-01T00:00:00+00:00\nbad,notanint,USD,2026-01-01T00:00:00+00:00\n');r=subprocess.run(['uv','run','ingest','--input',str(d/'i.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv'),'--strict'],capture_output=True);print(r.returncode)"` |
| note | Expected output: `2`. | — |
| AC-15 | When `--input` names a non-existent file, the exit code is `2`. | `python3 -c "import subprocess,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());r=subprocess.run(['uv','run','ingest','--input',str(d/'missing.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);print(r.returncode)"` |
| note | Expected output: `2`. | — |
| AC-16 | When `--input` names a non-existent file, a human-readable message is printed to stderr. | `python3 -c "import subprocess,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());r=subprocess.run(['uv','run','ingest','--input',str(d/'missing.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True,text=True);print('ok' if r.stderr.strip() else 'empty')"` |
| note | Expected output: `ok`. | — |
| AC-17 | When `--input` names a non-existent file, neither `--output` nor `--quarantine` files are created. | `python3 -c "import subprocess,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());subprocess.run(['uv','run','ingest','--input',str(d/'missing.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);print('clean' if not (d/'o.parquet').exists() and not (d/'q.csv').exists() else 'files_created')"` |
| note | Expected output: `clean`. | — |
| AC-18 | A header-only (empty) input file exits with code `1`. | `python3 -c "import subprocess,tempfile,pathlib;d=pathlib.Path(tempfile.mkdtemp());(d/'e.csv').write_text('id,amount_minor,currency,occurred_at\n');r=subprocess.run(['uv','run','ingest','--input',str(d/'e.csv'),'--output',str(d/'o.parquet'),'--quarantine',str(d/'q.csv')],capture_output=True);print(r.returncode)"` |
| note | Expected output: `1`. | — |
| AC-19 | A header-only input produces an empty Parquet file with the correct four-column schema and correct Int64 dtype for `amount_minor`; the quarantine CSV has the five-column header and no data rows; stdout is `read=0 valid=0 quarantined=0`. | `uv run pytest probes/test_probe.py -q -k test_missing_and_empty_input 2>&1 \| tail -2` |
| note | Expected output: `1 passed in ...`. | — |
| AC-20 | `README.md` exists at the repository root. | `test -f README.md && echo present` |
| AC-21 | `README.md` contains a `uv sync` step in the quickstart. | `python3 -c "t=open('README.md').read(); print('ok' if 'uv sync' in t else 'missing')"` |
| AC-22 | `README.md` contains a `uv run ingest` invocation example. | `python3 -c "t=open('README.md').read(); print('ok' if 'uv run ingest' in t else 'missing')"` |
