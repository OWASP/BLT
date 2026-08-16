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

### C3 — redact + history + triage deep-link
- Client-side redaction toggle (parity keys with `src/payload_redact.py`)
- Local send history for successful ingest (max 100)
- `url_launcher` → `{base}/triage.html?finding={id}`; triage UI auto-selects on load

## Exit criteria
- `cd client && flutter test` passes
- Scan `https://example.com` → preview → (optional redact) → send or queue
- History entry opens triage with the returned `finding_id`

## Follow-ups
| Slice | Notes |
|-------|--------|
| C4 | Packaging docs |
| Semgrep in-client | Optional; CLI `scripts/detect_export.py` already covers Semgrep→ingest |

## Demo credentials (loopback)
Same as `local_dev/send_finding.py`: `org-demo` / `scanner-1` / `k1` / `736563726574`
