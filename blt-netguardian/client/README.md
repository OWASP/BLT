# NetGuardian Flutter desktop client

Local producer for NetGuardian: configure org sender credentials, build a
`ztr-finding-1` envelope (HMAC-SHA256), and `POST /api/ingest`.

This is **client MR C1** — sign + send. Detection packs, offline queue, and
history land in follow-up MRs (C2/C3).

## Run (macOS)

From the repo root (with Flutter 3.x installed):

```bash
cd client
flutter pub get
flutter test
flutter run -d macos
```

Point **API base URL** at local `http://127.0.0.1:8787` (`python local_dev/serve.py`)
or a staging Worker. Demo secret `736563726574` / `org-demo` / `scanner-1` / `k1`
matches `local_dev/send_finding.py` (loopback only).

## Layout

| Path | Role |
|------|------|
| `lib/ingest/canonicalize.dart` | JCS-profile JSON + digests (parity with `src/canonicalize.py`) |
| `lib/ingest/envelope.dart` | Sign plaintext envelopes |
| `lib/ingest/ingest_client.dart` | HTTP POST + `X-BLT-Body-Digest` |
| `lib/config/sender_config.dart` | Persisted sender settings |
| `lib/main.dart` | Desktop UI |

## Spec

See [`docs/spec/flutter-client.md`](../docs/spec/flutter-client.md).
