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

`rate_limited` may include `"scope": "minute"` (RPM) or `"scope": "hour"` (RPH).
`Retry-After` is `60` for minute limits, or seconds until the next UTC hour for hour quotas.

Env knobs: `NG_INGEST_RPM` (default 60), `NG_INGEST_RPH` (default 1000). Set either to `0` to disable that gate.

Defined in `src/errors.py`.
