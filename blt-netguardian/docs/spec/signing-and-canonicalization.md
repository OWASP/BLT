# Signing and canonicalization (ztr-finding-1 v1)

**Status:** Locked for Week 1 implementation (Day 2). Changes require ADR + test updates.

---

## 1. Canonical JSON (JCS profile)

NetGuardian v1 uses an **RFC 8785 (JCS) compatible** serialization profile:

1. Start from the envelope object **with the `signature` key removed** (never sign the signature).
2. Recursively sort object keys by **lexicographic comparison of UTF-16 code unit sequences**: convert each key string to UTF-16 code units (including surrogate pairs as individual code units) and compare those sequences. This is **not** the same as Python’s default Unicode code-point ordering used by `json.dumps(..., sort_keys=True)` — keys that differ only in surrogate-pair vs BMP representation can sort differently under JCS vs `sort_keys=True`.
3. Serialize with `separators=(',', ':')`, `ensure_ascii=False`, UTF-8 encode the result. Reject non-finite numbers (`allow_nan=False` in Python).

Week 1 reference code in `src/ng/canonicalize.py` still uses `sort_keys=True` as a pragmatic interim; golden-vector tests must be updated before claiming full JCS compliance. Prefer a certified JCS implementation or explicit UTF-16 key sort when hardening.

**Reference implementation (interim):** `src/ng/canonicalize.py` → `canonicalize_envelope_for_signing()`.

---

## 2. Payload digest

`payload_digest` = lowercase hex(SHA-256(payload_bytes)) where:

- **Ciphertext mode:** `payload_bytes` = base64 decode of `payload_ciphertext`.
- **Plaintext mode:** `payload_bytes` = UTF-8 bytes of `canonicalize_json(payload_plaintext)` using the same rules as §1 (single object, no wrapper).

Verification order on ingest:

1. Parse JSON body; validate schema.
2. Recompute payload digest from declared mode; compare to `payload_digest` (`digest_mismatch` on failure).
3. Build signing document (envelope minus `signature`); canonicalize; HMAC verify.

---

## 3. Signing base string

```
signing_input = UTF8( canonicalize_envelope_for_signing(envelope_without_signature) )
signature     = HMAC_SHA256( key = sender_secret_for_kid, message = signing_input )
```

- Output encoding: **lowercase hex** (64 chars).
- Compare signatures in **constant time**.
- `kid` is part of the signed document (not header-only).

Optional HTTP header `X-BLT-Signature: sha256=<hex>` may duplicate the envelope `signature` field for proxies; server verifies the envelope field (and may cross-check header when present).

---

## 4. Key material

- Secrets live in Cloudflare **Secrets** / org key registry (`sender_keys` table stores metadata only, not raw secrets in D1).
- Rotation: multiple `kid` rows per `(org_id, sender_id)`; only `active=1` keys verify new ingest.

---

## 5. Golden vectors (tests)

See `tests/ng/fixtures/canonical_vectors.json` and `tests/ng/test_canonicalize.py`.

Vectors cover:

- Key ordering stability
- Unicode in `title` / `description`
- Plaintext vs ciphertext digest paths
- Signature changes when `kid` is tampered post-sign
