# Probe validation record — M-relay

## Inherited validation

The probe for M-relay is the S-ledger probe, unmodified. Validation is inherited by
byte-identity from `cases/S-ledger/probes/VALIDATION.md`. The full-pass and targeted-failure
transcripts recorded there apply directly to this probe.

**Byte-identity verification (run from the repository root):**

```bash
diff skills/agent-bench/cases/S-ledger/probes/test_probe.py \
     skills/agent-bench/cases/M-relay/probes/test_probe.py && echo identical
```

Expected output: `identical`

**Actual output at authoring time (2026-08-10):** `identical`

**Hash at authoring time:**

```
e1c51da861774f679ef59e9e700efba798d8fd89a636a6e83610d6f578265f1d  test_probe.py
```

This matches the hash in `cases/S-ledger/probes/SHA256SUMS` exactly.

## Why inherited validation is sufficient

The final state of M-relay leg 3 is the complete S-ledger contract. The probe suite tests
the full contract: 12 tests covering account management, credit, idempotent transfers,
transaction history, pagination, and UTC timezone round-trip. The S-ledger `VALIDATION.md`
records:

- Full-pass run: 12/12 passed against a reference implementation built from `spec/features.md`.
- Targeted-failure run: 2/12 failed (the two idempotency tests) when the idempotency key
  check was removed; all other tests remained green. The failing tests correctly isolated
  the broken requirement.

Because the probe file is byte-identical to the validated S-ledger probe, no separate
reference implementation is required or committed for M-relay.

## Probe defect log

No defects recorded. If a defect is found after this case is in use, follow the procedure
in `references/adding-a-case.md` (fix, bump version, regenerate SHA256SUMS, append a record
here). Do not delete or edit this section.
