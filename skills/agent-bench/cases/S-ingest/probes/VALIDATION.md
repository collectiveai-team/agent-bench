# Probe validation record — S-ingest

## Full-pass run

**Date:** 2026-08-08

**Reference directory:** `/tmp/agb-ingest-ref` (throwaway; not committed)

**Venv source:** created fresh with `uv venv .venv --python 3.12`, then
`uv pip install polars pytest`. Installed: polars 1.43.2, pytest 9.1.1. The
reference implementation (`/tmp/agb-ingest-ref/app/cli.py`) was written from
scratch against `spec/features.md` and was never committed.

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
collecting ... collected 8 items

tests/test_probe.py::test_all_valid_rows_pass_through_in_order PASSED    [ 12%]
tests/test_probe.py::test_bad_amount_quarantined_with_reason PASSED      [ 25%]
tests/test_probe.py::test_bad_currency_quarantined_with_reason PASSED    [ 37%]
tests/test_probe.py::test_naive_timestamp_quarantined PASSED             [ 50%]
tests/test_probe.py::test_duplicate_id_quarantines_the_later_row PASSED  [ 62%]
tests/test_probe.py::test_first_failing_rule_wins PASSED                 [ 75%]
tests/test_probe.py::test_exit_codes PASSED                              [ 87%]
tests/test_probe.py::test_missing_and_empty_input PASSED                 [100%]

============================== 8 passed in 1.58s ==============================
```

**Result:** 8/8 passed. All probes pass against this known-good implementation.

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
# BROKEN: keeps later row instead of first (for deliberate-break validation)
# if id_val in seen_ids:
#     return "id"
```

With this break, duplicate ids are never quarantined — both the first and all
later occurrences are treated as valid (subject only to the remaining rules). This
simulates a naive implementation that omits duplicate-id detection.

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
collecting ... collected 8 items

tests/test_probe.py::test_all_valid_rows_pass_through_in_order PASSED    [ 12%]
tests/test_probe.py::test_bad_amount_quarantined_with_reason PASSED      [ 25%]
tests/test_probe.py::test_bad_currency_quarantined_with_reason PASSED    [ 37%]
tests/test_probe.py::test_naive_timestamp_quarantined PASSED             [ 50%]
tests/test_probe.py::test_duplicate_id_quarantines_the_later_row FAILED  [ 62%]
tests/test_probe.py::test_first_failing_rule_wins PASSED                 [ 75%]
tests/test_probe.py::test_exit_codes PASSED                              [ 87%]
tests/test_probe.py::test_missing_and_empty_input PASSED                 [100%]

=================================== FAILURES ===================================
_________________ test_duplicate_id_quarantines_the_later_row __________________

tmp_path = PosixPath('/private/var/folders/fr/1hzjgk3n61z65276whgbl5v40000gn/T/pytest-of-lionelchamorro/pytest-1925/test_duplicate_id_quarantines_0')

    def test_duplicate_id_quarantines_the_later_row(tmp_path):
        ...
        result = _run(inp, out, quar)

        assert result.returncode == 0
>       assert result.stdout.strip() == "read=3 valid=2 quarantined=1"
E       AssertionError: assert 'read=3 valid=3 quarantined=0' == 'read=3 valid=2 quarantined=1'
E
E         - read=3 valid=2 quarantined=1
E         ?              ^             ^
E         + read=3 valid=3 quarantined=0
E         ?              ^             ^

tests/test_probe.py:216: AssertionError
=========================== short test summary info ============================
FAILED tests/test_probe.py::test_duplicate_id_quarantines_the_later_row - Ass...
========================= 1 failed, 7 passed in 0.90s ==========================
```

**Result:** Exactly 1 failure (`test_duplicate_id_quarantines_the_later_row`).
All 7 other probe tests continued to pass. The probe correctly discriminates
the duplicate-id quarantine requirement.

## Cleanup

After both validation runs the throwaway reference was deleted:

```bash
rm -rf /tmp/agb-ingest-ref
test ! -e /tmp/agb-ingest-ref && echo "reference deleted"
→ reference deleted
```

The reference existed only in `/tmp/agb-ingest-ref` and is now gone.
