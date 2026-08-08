# Rubric — S-ingest

Dimension names are fixed by `references/evaluator-4-judge.md`. Anchors are
written for this case from scratch. Weights are adjusted from the L-family
defaults; see the note below.

**Reweighting rationale:** Two dimensions are reduced from the L-family defaults.

*Concurrency and async correctness* drops from 10% to 2% (freeing 8%). S-ingest
is a synchronous CLI with no async I/O, no event loop, no concurrent execution
path, and no WebSocket surface. There is no meaningful correctness signal in the
concurrency dimension for a process that reads one CSV, writes two output files,
and exits. The dimension is retained at 2% so that a truly egregious violation
(e.g. spawning unsynchronised threads that corrupt the output files) still
registers in the score.

*Code quality and idiom* drops from 10% to 8% (freeing 2%). For a short CLI of
approximately 100–150 LOC, style differences between arms are a weaker
discriminator than correctness and schema adherence.

The freed 10% is redistributed: +5% to Spec fidelity (the rule-evaluation
order, the exact exit-code precedence table, and the empty-file schema are the
primary discriminators for this case) and +5% to Correctness and robustness
(validation logic, quarantine column fidelity, stdout format, and missing-file
handling are the second discriminator).

Net weights: 30 + 25 + 15 + 15 + 2 + 8 + 5 = **100%**. Arithmetic verified.

Score each dimension 1–5 (absolute protocol). Every score must cite at least one
`file:line` reference or command output; a score without evidence is discarded.
Do not reward code volume, comment density, or defensive boilerplate.

| Dimension | Weight | 1 | 3 | 5 |
|---|---|---|---|---|
| Spec fidelity | 30% | rule order not implemented or exit codes wrong (e.g. exit 1 instead of 2 for missing file); quarantine reason column missing or misnamed | rule order mostly correct; one exit code wrong or one edge case missed (e.g. `--strict` with no quarantine not returning 0) | all four rules evaluated in spec order; exit-code precedence table exact (missing file → 2, strict+quarantined → 2, none-valid → 1, any-valid → 0); summary line exact format; empty-file parquet schema correct |
| Correctness and robustness | 25% | quarantine produces wrong rows or reasons; duplicate id check absent or inverted; output files created even when input is missing | most validation rules correct; one silent defect (e.g. float "12.5" not caught because validator checks `isinstance` instead of `int()` on the string value; or duplicate id check tracks only valid rows) | all validation rules correct; duplicate check tracks all seen ids regardless of prior quarantine reason; missing-input guard fires before any file writes; `--strict` overrides base exit code correctly; parquet and quarantine both written atomically (no half-written outputs on error paths) |
| Architecture and layering | 15% | all logic in one flat script with no separation; parsing, validation, I/O tangled together | CLI parsing and core processing are separated; validation logic extractable but mixed with I/O | clean separation: argument parsing → validation function(s) → output writing; validation function is pure (takes a row + seen-ids set, returns first failing rule or None); no business logic in the argparse block |
| Test quality | 15% | no tests beyond the scaffold placeholder, or tests that only test happy path with no invalid-input cases | key rules tested; some edge cases thin (e.g. rule ordering not tested; empty-file behavior untested) | independent, deterministic tests cover all four validation rules, duplicate detection, rule ordering, all three exit codes, missing file, and empty file; tests use temp files and do not depend on execution order |
| Concurrency and async correctness | 2% | output files corrupted by concurrent writes from unsynchronised threads | single-threaded sequential execution with no observable concurrency defects | clean, single-threaded; no threading, no async, no shared mutable state outside the local scope of `main()` |
| Code quality and idiom | 8% | untyped, dead code, magic strings scattered, no constants | typed and readable; validation logic not duplicated; column names as constants or literals used consistently | idiomatic: type annotations throughout; column names as a single source of truth; regex compiled once or via `re.fullmatch`; polars schema declared explicitly rather than inferred; ruff-clean |
| Docs and DX | 5% | README missing or no quickstart | quickstart present (`uv sync`, invocation example) but missing column rules or exit code table | accurate ops story: quickstart (`uv sync` + `uv run ingest` example), all four column names with their rules, exit code table |
