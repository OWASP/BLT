# Stable ingest error codes (ztr-finding-1)

All error responses use JSON: `{ "error": "<code>", "message": "human-readable detail" }`.

| Code | HTTP | When |
|------|------|------|
| `invalid_envelope` | 400 | JSON/schema violation, missing required field, dual payload modes |
| `invalid_payload_mode` | 400 | `plaintext_mode` inconsistent with payload fields |
| `digest_mismatch` | 400 | `payload_digest` or `X-BLT-Body-Digest` does not match body |
| `clock_skew` | 400 | `issued_at` outside ±5 minute window |
| `bad_signature` | 401 | HMAC verification failed |
| `unknown_kid` | 401 | `kid` not registered or inactive for sender/org |
| `payload_too_large` | 413 | Body over org/default 1 MiB cap |
| `rate_limited` | 429 | Throttle / back-pressure; include `Retry-After` |

Python constants: `src/ng/errors.py`.
