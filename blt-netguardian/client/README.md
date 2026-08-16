# Flutter desktop client

## C1 — sign + send
Configure org sender credentials, build `ztr-finding-1`, `POST /api/ingest`.

## C2 — detect → preview → queue
HTTP header scan against a target URL, checkbox preview, sign/send selected,
and a persistent outbox with retry for offline/failed posts.

## C3 — redact + history + triage deep-link
- Toggle client-side secret redaction before queue/send
- Local send history (finding_id + rule/target)
- Open triage in browser (`/triage.html?finding=…`)

## Run (macOS)

Terminal 1 — API from the **repo root**:

```bash
python local_dev/serve.py
```

Terminal 2 — client:

```bash
cd client
flutter pub get
flutter test
flutter run -d macos
```

Demo secret `736563726574` / `org-demo` / `scanner-1` / `k1` (loopback only).

## Layout

| Path | Role |
|------|------|
| `lib/detect/` | HTTP header detector + fingerprint normalize |
| `lib/ingest/` | Canonicalize, sign, HTTP ingest, redact |
| `lib/history/` | Local send history |
| `lib/queue/outbox.dart` | Offline outbox + retry |
| `lib/main.dart` | Desktop UI |

## Spec

See [`docs/spec/flutter-client.md`](../docs/spec/flutter-client.md).
