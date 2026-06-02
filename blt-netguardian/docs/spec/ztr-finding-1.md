# ztr-finding-1 — ingestion envelope specification (v1)

**Status:** Week 1 draft (Days 1–2). Mentor review before ingest implementation freeze.

**Scope:** NetGuardian GSoC 2026 — Cloudflare Worker + D1 + R2. CVE and Issue creation delegate to BLT-API; this contract is shared by the BLT-NetGuardian scanner exporter, Flutter desktop client, and CI agents.

**Related:** [signing-and-canonicalization.md](signing-and-canonicalization.md), [error-codes.md](error-codes.md), [../../migrations/ng/0001_core.sql](../../migrations/ng/0001_core.sql), OpenAPI stub at [../../openapi/netguardian.yaml](../../openapi/netguardian.yaml).

---

## 1. Purpose

`ztr-finding-1` is a signed JSON envelope that carries one security finding (and optional evidence metadata) from a trusted producer (`sender_id`) into an org-scoped NetGuardian tenant. Goals:

- **Integrity** — `payload_digest` binds exact payload bytes; HMAC binds the canonical envelope.
- **Authenticity** — only holders of the active `kid` secret can produce valid signatures.
- **Replay resistance** — unique `(org_id, sender_id, nonce)` with clock-skew checks.

---

## 2. Envelope fields

### 2.1 Required top-level fields

| Field | Type | Constraints |
|-------|------|-------------|
| `version` | string | Must be exactly `"ztr-finding-1"`. |
| `org_id` | string | Tenant scope; must match authenticated org for ingest. |
| `sender_id` | string | Stable producer identity within `org_id`. |
| `kid` | string | Key id for HMAC verification; must exist in `sender_keys` for `(org_id, sender_id, kid)`. |
| `alg` | string | Must be `"hmac-sha256"` for v1. |
| `issued_at` | string | RFC 3339 UTC timestamp (e.g. `2026-05-28T12:00:00Z`). |
| `nonce` | string | Unique per `(org_id, sender_id)`; recommended `<unix_ts>-<random>`. |
| `payload_digest` | string | Lowercase hex SHA-256 over **exact payload bytes** (see §4). |
| `signature` | string | Lowercase hex HMAC-SHA256 (see [signing-and-canonicalization.md](signing-and-canonicalization.md)). |

### 2.2 Payload mode (exactly one)

| Mode | Required fields | Rules |
|------|-----------------|-------|
| Plaintext | `plaintext_mode: true`, `payload_plaintext` (object) | Digest = SHA-256 of UTF-8 canonical JSON of `payload_plaintext` (same rules as signing canonicalization, applied to the payload object only). |
| Ciphertext | `payload_ciphertext` (string, base64) | `plaintext_mode` absent or `false`. Digest = SHA-256 of decoded ciphertext bytes. |

**Invalid:** both payloads set, neither set, or `plaintext_mode: true` without `payload_plaintext`.

### 2.3 Finding payload (`payload_plaintext` shape)

Minimum fields for v1 triage (additional keys allowed if documented in OpenAPI):

| Field | Type | Notes |
|-------|------|-------|
| `rule_id` | string | Detector / rule identifier. |
| `severity` | string | One of `critical`, `high`, `medium`, `low`, `info`. |
| `title` | string | Short human title. |
| `target` | string | URL, repo, or asset identifier. |
| `description` | string | Optional long text. |
| `fingerprint` | string | Optional dedup key; server may compute if omitted. |
| `cve_id` | string | Optional normalized CVE id. |
| `evidence` | array | Optional inline evidence items (see §5). |

### 2.4 Transport headers (HTTP)

| Header | Required | Semantics |
|--------|----------|-----------|
| `Content-Type` | Yes | `application/json` |
| `X-BLT-Body-Digest` | Yes | `sha256=<hex>` over raw request body bytes (must match recomputed digest). |
| `X-BLT-Timestamp` | Advisory | Unix seconds; used for logging/rate limits; **trust** comes from `issued_at` in envelope. |

---

## 3. Freshness and replay

- **Clock skew:** reject if `issued_at` is outside **±5 minutes** of server time (`clock_skew`).
- **Nonce uniqueness:** D1 `UNIQUE (org_id, sender_id, nonce)`.
- **Duplicate ingest:** return **200** with `{ "status": "duplicate", "replay": true, "finding_id": "..." }` (idempotent).
- **New ingest:** return **201** with `{ "status": "created", "finding_id": "...", "replay": false }`.

Per-sender replay windows may be tightened org-wide later; v1 uses global ±5 minutes.

---

## 4. Size limits

- Default max request body: **1 MiB** (1,048,576 bytes) → `payload_too_large` (413).
- Inline evidence per item: cap documented in OpenAPI (default 64 KiB per item, 256 KiB total inline per envelope).

---

## 5. Evidence

**Inline** (in `payload_plaintext.evidence[]`):

```json
{
  "media_type": "text/plain",
  "content_base64": "...",
  "filename": "optional"
}
```

**Large / binary:** use R2 upload flow (Week 2+); D1 `evidence_meta` stores `r2_key`, `digest`, `size_bytes`. Object key pattern: `org/{org_id}/{digest}?v=K`.

---

## 6. HTTP responses (ingest)

| Status | When | Body example |
|--------|------|----------------|
| 201 | New envelope accepted | `{ "status": "created", "finding_id": "fnd_01HXYZ...", "replay": false }` |
| 200 | Duplicate nonce | `{ "status": "duplicate", "finding_id": "fnd_01HXYZ...", "replay": true }` |
| 400 | Validation / skew / digest | `{ "error": "clock_skew", "message": "issued_at outside ±5 minute window" }` — codes in [error-codes.md](error-codes.md) |
| 401 | Bad signature / unknown kid | `{ "error": "bad_signature", "message": "HMAC verification failed" }` or `{ "error": "unknown_kid", "message": "kid not registered for sender" }` |
| 413 | Body too large | `{ "error": "payload_too_large", "message": "request body exceeds 1048576 bytes" }` |
| 429 | Rate limit | `{ "error": "rate_limited", "message": "too many requests" }` + `Retry-After` header |

Batch ingest (`POST /api/ng/ingest/batch`): **207** with per-index results (Week 2).

---

## 7. PR #5057 alignment (CVE)

Findings may carry `cve_id` at ingest; Worker enriches via BLT-API using the same normalization as BLT `website/cache/cve_cache.py` (`normalize_cve_id`, cached scores). NetGuardian does not re-implement CVE feeds in v1.

---

## 8. Week 1 exit checklist

- [x] Field list and payload modes documented (this file)
- [x] Error enum documented
- [x] JCS / signing base string documented
- [x] D1 table sketch in `migrations/ng/0001_core.sql`
- [ ] Migrations applied to staging D1
- [ ] Canonicalization helpers + tests green in CI
- [ ] Mentor ACK
