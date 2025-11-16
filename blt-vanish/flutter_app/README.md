# SelfErase Flutter App

The local Flutter application for SelfErase - handles all sensitive personal data locally and encrypted.

## Features

- **Encrypted Local Storage**: All PII encrypted with AES-256
- **Offline-First**: Works without internet connection
- **Cross-Platform**: iOS, Android, macOS, Windows, Linux
- **Privacy-First**: No data ever leaves your device

## Getting Started

### Prerequisites

- Flutter 3.0 or later
- Dart 3.0 or later

### Installation

```bash
# Install dependencies
flutter pub get

# Generate code (for JSON serialization)
flutter pub run build_runner build

# Run the app
flutter run
```

### Building

```bash
# Android
flutter build apk --release

# iOS (macOS only)
flutter build ios --release

# Desktop
flutter build macos --release  # macOS
flutter build windows --release  # Windows
flutter build linux --release  # Linux
```

## Architecture

```
lib/
├── main.dart              # App entry point
├── models/                # Data models
│   ├── broker.dart        # Broker data model
│   ├── user_data.dart     # User's personal data (encrypted)
│   └── opt_out_request.dart  # Opt-out request tracking
├── services/              # Business logic
│   ├── storage_service.dart  # Encrypted local storage
│   └── broker_service.dart   # Broker data fetching (public only)
├── screens/               # UI screens
│   ├── home_screen.dart
│   ├── brokers_screen.dart
│   ├── broker_detail_screen.dart
│   ├── profile_screen.dart
│   └── requests_screen.dart
└── widgets/               # Reusable UI components
```

## Security

- All PII stored encrypted with AES-256-GCM
- Keys stored in platform secure storage (Keychain/KeyStore)
- No network transmission of PII
- No analytics or tracking
- Open-source and auditable

## Testing

```bash
# Run all tests
flutter test

# Run with coverage
flutter test --coverage

# View coverage
genhtml coverage/lcov.info -o coverage/html
open coverage/html/index.html
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

AGPL-3.0 - See [LICENSE](../LICENSE)
