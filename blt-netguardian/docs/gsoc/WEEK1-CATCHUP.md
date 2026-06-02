# Week 1 catch-up log (through Day 3)

**Repo:** [Pritz395/BLT-NetGuardian](https://github.com/Pritz395/BLT-NetGuardian) (fork; upstream `OWASP-BLT/BLT-NetGuardian` not public yet)

| Day | Proposal focus | Status | Artifacts |
|-----|----------------|--------|-----------|
| 1 | `ztr-finding-1` fields + error enums | Done | [spec/ztr-finding-1.md](../spec/ztr-finding-1.md), [spec/error-codes.md](../spec/error-codes.md), `src/ng/errors.py` |
| 2 | JCS + signing base string + spec one-pager | Done | [spec/signing-and-canonicalization.md](../spec/signing-and-canonicalization.md) |
| 3 | D1 tables + constraints sketch | Done | [migrations/ng/0001_core.sql](../../migrations/ng/0001_core.sql) |

**Ahead of schedule (Days 4–6 helpers, not ingest routes yet):**

- `src/ng/canonicalize.py` + `tests/ng/test_canonicalize.py`
- [openapi/netguardian.yaml](../../openapi/netguardian.yaml)
- CI checks migration file present

## Next (Day 4+)

1. Apply `migrations/ng/0001_core.sql` to staging D1 (`wrangler d1 execute …`).
2. Wire `/api/ng/ingest` in `src/worker.py` (Week 2 scope).
3. Open PR to OWASP-BLT when org repo is available.

## Mentor paste (Days 1–3)

> Week 1 Days 1–3: Locked `ztr-finding-1` field list, payload modes, stable error codes, JCS-profile canonicalization + HMAC signing rules, and D1 schema (`sender_keys`, `envelopes`, `findings`, `evidence_meta`, `access_logs`, `events_outbox`, `ng_metrics`) with `UNIQUE(org_id, sender_id, nonce)`. Canonicalize/digest unit tests passing locally. No ingest handler yet — Week 2.
