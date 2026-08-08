# Probe validation record — S-ingest

## Full-pass run

**Date:** 2026-08-08

**Reference directory:** `/tmp/agb-ingest-ref` (throwaway; not committed)

**Venv source:** created fresh with `uv venv .venv --python 3.12`, then
`uv pip install --python .venv/bin/python polars pytest`. Installed: polars 1.43.2,
pytest 9.1.1. The reference implementation (`/tmp/agb-ingest-ref/app/cli.py`)
was written from scratch against `spec/features.md` and was never committed.

**Command used:**

```bash
cp skills/agent-bench/cases/S-ingest/probes/test_probe.py /tmp/agb-ingest-ref/tests/test_probe.py
cd /tmp/agb-ingest-ref && ./.venv/bin/python -m pytest tests/test_probe.py -v
```

**Output:**

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0 -- /private/tmp/agb-ingest-ref/.venv/bin/python
cachedir: .pytest_cache
rootdir: /private/tmp/agb-ingest-ref
configfile: pyproject.toml
collecting ... collected 9 items

tests/test_probe.py::test_all_valid_rows_pass_through_in_order PASSED    [ 11%]
tests/test_probe.py::test_bad_amount_quarantined_with_reason PASSED      [ 22%]
tests/test_probe.py::test_bad_currency_quarantined_with_reason PASSED    [ 33%]
tests/test_probe.py::test_naive_timestamp_quarantined PASSED             [ 44%]
tests/test_probe.py::test_duplicate_id_quarantines_the_later_row PASSED  [ 55%]
tests/test_probe.py::test_first_failing_rule_wins PASSED                 [ 66%]
tests/test_probe.py::test_exit_codes PASSED                              [ 77%]
tests/test_probe.py::test_missing_and_empty_input PASSED                 [ 88%]
tests/test_probe.py::test_duplicate_id_when_first_occurrence_quarantined PASSED [100%]

============================== 9 passed in 4.68s ==============================
```

**Result:** 9/9 passed. All probes pass against this known-good implementation.

Note: the probe invokes the CLI via `uv run ingest` (a subprocess). The reference
`pyproject.toml` includes `[tool.hatch.build.targets.wheel] packages = ["app"]`
because hatchling's default heuristic looks for a directory named after the project
(`ingest`), not `app`. Solver implementations built with this config work correctly;
the BOOTSTRAP.md scaffold includes this table entry to spare solvers from this
hatchling pitfall.

## Targeted-failure run

**Date:** 2026-08-08

**Break applied:** One change to the throwaway implementation in
`/tmp/agb-ingest-ref/app/cli.py`. In `_validate_row`, the id-uniqueness check
was commented out:

```python
# 2. id unique — BROKEN: keeps later row instead of first (deliberate-break validation)
# if id_val in seen_ids:
#     return "id"
```

With this break, duplicate ids are never quarantined — both the first and all
later occurrences are treated as valid (subject only to the remaining rules). This
simulates a naive implementation that omits duplicate-id detection entirely,
including the case where the first occurrence was quarantined for another reason.

**Command used:**

```bash
cd /tmp/agb-ingest-ref && ./.venv/bin/python -m pytest tests/test_probe.py -v
```

**Output:**

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0 -- /private/tmp/agb-ingest-ref/.venv/bin/python
cachedir: .pytest_cache
rootdir: /private/tmp/agb-ingest-ref
configfile: pyproject.toml
collecting ... collected 9 items

tests/test_probe.py::test_all_valid_rows_pass_through_in_order PASSED    [ 11%]
tests/test_probe.py::test_bad_amount_quarantined_with_reason PASSED      [ 22%]
tests/test_probe.py::test_bad_currency_quarantined_with_reason PASSED    [ 33%]
tests/test_probe.py::test_naive_timestamp_quarantined PASSED             [ 44%]
tests/test_probe.py::test_duplicate_id_quarantines_the_later_row FAILED  [ 55%]
tests/test_probe.py::test_first_failing_rule_wins PASSED                 [ 66%]
tests/test_probe.py::test_exit_codes PASSED                              [ 77%]
tests/test_probe.py::test_missing_and_empty_input PASSED                 [ 88%]
tests/test_probe.py::test_duplicate_id_when_first_occurrence_quarantined FAILED [100%]

=================================== FAILURES ===================================
_________________ test_duplicate_id_quarantines_the_later_row __________________

    def test_duplicate_id_quarantines_the_later_row(tmp_path):
        ...
        assert result.returncode == 0
>       assert result.stdout.strip() == "read=3 valid=2 quarantined=1"
E       AssertionError: assert 'read=3 valid=3 quarantined=0' == 'read=3 valid=2 quarantined=1'
E
E         - read=3 valid=2 quarantined=1
E         + read=3 valid=3 quarantined=0

tests/test_probe.py:216: AssertionError
_____________ test_duplicate_id_when_first_occurrence_quarantined ______________

    def test_duplicate_id_when_first_occurrence_quarantined(tmp_path):
        ...
>       assert result.stdout.strip() == "read=3 valid=1 quarantined=2"
E       AssertionError: assert 'read=3 valid=2 quarantined=1' == 'read=3 valid=1 quarantined=2'
E
E         - read=3 valid=1 quarantined=2
E         + read=3 valid=2 quarantined=1

tests/test_probe.py:399: AssertionError
=========================== short test summary info ============================
FAILED tests/test_probe.py::test_duplicate_id_quarantines_the_later_row
FAILED tests/test_probe.py::test_duplicate_id_when_first_occurrence_quarantined
======================= 2 failed, 7 passed in 1.13s ==========================
```

**Result:** Exactly 2 failures (`test_duplicate_id_quarantines_the_later_row` and
`test_duplicate_id_when_first_occurrence_quarantined`). All 7 other probe tests
continued to pass. Both duplicate-id tests correctly catch the break. The reviewer
anticipated this: "with Important 1 added, that break may now fail two tests rather
than one — if so, that is correct and expected."

## Cleanup

After both validation runs the throwaway reference was deleted:

```bash
rm -rf /tmp/agb-ingest-ref
test ! -e /tmp/agb-ingest-ref && echo "reference deleted"
→ reference deleted
```

The reference existed only in `/tmp/agb-ingest-ref` and is now gone.
