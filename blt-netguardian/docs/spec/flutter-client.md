# Flutter desktop client

Desktop producer that **finds** and **sends** signed findings into NetGuardian.

## Shipped

### C1 — sign + POST
- Sender config UI + HMAC `ztr-finding-1` + `POST /api/ingest`
- Golden-vector tests vs Python canonicalize/sign

### C2 — detect → preview → queue
- Local HTTP header scan (parity subset of `src/detect/http_headers.py`)
- Preview + multi-select before send
- Persistent outbox (`shared_preferences`) with retry / clear-sent

## Exit criteria
- `cd client && flutter test` passes
- Scan `https://example.com` → preview findings → send or queue against local/staging ingest

## Follow-ups
| Slice | Notes |
|-------|--------|
| C3 | Redaction toggles + history + triage deep-link |
| C4 | Packaging docs |
| Semgrep in-client | Optional; CLI `scripts/detect_export.py` already covers Semgrep→ingest |

## Demo credentials (loopback)
Same as `local_dev/send_finding.py`: `org-demo` / `scanner-1` / `k1` / `736563726574`
