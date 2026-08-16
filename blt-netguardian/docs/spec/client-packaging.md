# Client packaging (C4)

Build artifacts from `client/`. Demo credentials are **loopback-only**.

## macOS

```bash
cd client
flutter pub get
flutter test
flutter build macos --release
```

Artifact: `client/build/macos/Build/Products/Release/netguardian_client.app`

- Sandbox entitlements include `network.client` (scan + ingest) and `network.server`.
- `NSAllowsLocalNetworking` is set so `http://127.0.0.1:8787` works.
- Notarization / Developer ID signing is operator-specific (`codesign`, `notarytool`).

## Windows

```bash
cd client
flutter build windows --release
```

Artifact: `client/build/windows/x64/runner/Release/`

## Linux

```bash
cd client
flutter build linux --release
```

Artifact: `client/build/linux/x64/release/bundle/`

## Staging

1. Point API base URL at the Worker origin (HTTPS).
2. Do **not** use demo HMAC / payload key.
3. Enable **Encrypt payload** and set the org AES-256 key (base64, 32 bytes).
4. `Ping API` must show LIVE before send.
