# Flutter desktop client

HUD-styled producer matching web triage: detect → redact → AES-GCM encrypt → HMAC sign → `POST /api/ingest`.

## Slices
- **C1** sign + send
- **C2** HTTP header scan, preview, outbox
- **C3** redaction, send history, triage `?finding=`
- **C4** encrypt + packaging ([docs](../docs/spec/client-packaging.md))

## Run (macOS)

Terminal 1 — API from the **repo root**:

```bash
python3 local_dev/serve.py
```

Terminal 2 — client:

```bash
cd client
flutter pub get
flutter test
flutter run -d macos
```

No-signup one-liner (scans **from your machine**, signs with the install HMAC key):

```bash
curl -fsSL https://netguardian.owaspblt.org/install.sh | sh -s -- https://your-site.example
```

Pass a host you are allowed to test. Demo HMAC: `736563726574` / `org-demo` / `scanner-1` / `k1`.  
Payload key: `netguardian-demo-aesgcm-key-0032`.

## Layout

| Path | Role |
|------|------|
| `lib/theme/hud.dart` | Triage HUD tokens + panels |
| `lib/detect/` | HTTP header detector (Python parity) |
| `lib/ingest/` | Canonicalize, sign, AES-GCM, HTTP ingest, redact |
| `lib/history/` | Local send history |
| `lib/queue/outbox.dart` | Offline outbox + retry |
| `lib/main.dart` | Desktop UI |
