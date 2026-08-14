# Flutter desktop client (C1)

Desktop producer that finds (later) and **sends** signed findings into NetGuardian.

## C1 scope (this MR)

- Flutter desktop scaffold (`client/`, macOS/Linux/Windows)
- Sender config: base URL, `org_id`, `sender_id`, `kid`, HMAC secret hex
- Build `ztr-finding-1` plaintext envelopes with HMAC-SHA256 (parity with `src/envelope.py`)
- `POST /api/ingest` with `X-BLT-Body-Digest: sha256=…`
- Unit tests against a Python golden signature vector

## Exit criterion

`flutter test` passes; app can send a demo finding to local/staging ingest.

## Follow-ups

| MR | Slice |
|----|--------|
| C2 | Detect → preview → offline queue + retry |
| C3 | Redaction toggles + local history + triage deep-link |
| C4 | Packaging / portable build notes |

## Demo credentials (loopback)

Same as `local_dev/send_finding.py`:

- `org_id=org-demo`
- `sender_id=scanner-1`
- `kid=k1`
- `secret_hex=736563726574`
