# Flutter desktop client

Desktop producer that **finds** and **sends** signed findings into NetGuardian.
Visual language matches the web triage HUD (Orbitron / Share Tech Mono, red `#ff2020`).

## Shipped

### C1 — sign + POST
- Sender config UI + HMAC `ztr-finding-1` + `POST /api/ingest`
- Golden-vector tests vs Python canonicalize/sign

### C2 — detect → preview → queue
- Local HTTP header scan (**full parity** with `src/detect/http_headers.py`)
- Preview + multi-select before send
- Persistent outbox (`shared_preferences`) with retry / clear-sent

### C3 — redact + history + triage deep-link
- Client-side redaction toggle (parity keys with `src/payload_redact.py`)
- Local send history for successful ingest (max 100)
- `url_launcher` → `{base}/triage.html?finding={id}`; triage UI auto-selects on load

### C4 — encrypt + packaging
- AES-256-GCM encrypt path (AAD = `org_id`, wire format = Python `payload_crypto`)
- macOS `network.client` entitlements + local ATS
- Packaging notes: [`docs/spec/client-packaging.md`](client-packaging.md)

## Exit criteria
- `cd client && flutter test` passes
- Scan `https://example.com` → preview → redact/encrypt → send or queue
- History entry opens triage with the returned `finding_id`
- Encrypted ingest decrypts on authorized finding detail

## Demo credentials (loopback)
Same as `local_dev/send_finding.py`: `org-demo` / `scanner-1` / `k1` / `736563726574`  
Payload key: `netguardian-demo-aesgcm-key-0032` (base64 in the client default).
