# Acceptance gates (W7)

Golden fixtures live in `tests/fixtures/acceptance_cases.json`.
The runner is `tests/test_acceptance_gates.py`.

## Thresholds

| Gate | Threshold | How measured |
|------|-----------|--------------|
| Ingest accept success | **≥ 95%** | Fraction of `kind: accept` cases that hit expected HTTP status + `body.status` |
| Reject correctness | **100%** | Every `kind: reject` case must raise/return the expected error code |

CSV/CVE enrichment accuracy (≥90%) is deferred until the detection pack ships; this pack only gates the **ingest contract**.

## Run locally

```bash
cd BLT-NetGuardian
.venv/bin/python -m pytest tests/test_acceptance_gates.py -q
```

Optional summary script:

```bash
.venv/bin/python scripts/acceptance_run.py
```

## Adding a fixture

1. Append an object to `cases` in `acceptance_cases.json`.
2. Set `kind` to `accept` or `reject`.
3. For accept cases, set `expect.status` and `expect.body_status` (`created` / `duplicate` / `merged`).
4. For reject cases, set `expect.error` and `expect.http_status`.
5. Re-run the gate test — do not lower the threshold to make a bad case pass.

## Relationship to midterm E2E

`test_midterm_e2e.py` proves one happy path (ingest → triage → convert → CSV).
Acceptance gates prove a **matrix** of contract behaviors so detection and quota work later can measure against known outcomes.
