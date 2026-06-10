# Ingest error codes

JSON shape: `{ "error": "<code>", "message": "..." }`

| Code | HTTP |
|------|------|
| `invalid_envelope` | 400 |
| `invalid_payload_mode` | 400 |
| `digest_mismatch` | 400 |
| `clock_skew` | 400 |
| `bad_signature` | 401 |
| `unknown_kid` | 401 |
| `payload_too_large` | 413 |
| `rate_limited` | 429 |

Defined in `src/ingest/errors.py`.
