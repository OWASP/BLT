# SelfErase

**An open-source, hybrid local+edge privacy toolkit for managing and deleting personal data online.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Security: Zero PII](https://img.shields.io/badge/Security-Zero%20PII-green.svg)](./SECURITY.md)

## 🎯 Design Goal

SelfErase helps individuals identify, manage, and remove their personal data from data brokers—**without ever sharing personal information with any external service.**

This is a **security-first, zero-data-retention system** where:
- ✅ All personal data stays encrypted on your local device
- ✅ No third-party servers ever see your PII
- ✅ You maintain complete ownership and control
- ✅ Works fully offline when needed
- ✅ Open-source and independently verifiable

## 🏗️ Architecture

SelfErase uses a **hybrid model** that combines local security with edge automation:

```
┌─────────────────────────────┐
│   GitHub (Code Only)        │
│  • Documentation            │
│  • Broker metadata          │
│  • Source code              │
└──────────────┬──────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Cloudflare Workers           │
│  • Public metadata APIs      │
│  • Broker health checks      │
│  • Opt-out templates         │
│  • No user data ever         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Local Flutter App            │
│  • Encrypted PII storage     │
│  • Opt-out generator         │
│  • User dashboard            │
│  • Offline capable           │
│  • Your device only          │
└──────────────────────────────┘
```

### Local Flutter App (User-Controlled)

The Flutter app runs on iOS, Android, macOS, Windows, and Linux:

- **Handles all sensitive personal data locally**
- Stores data encrypted with AES-256 / SQLCipher
- Generates and tracks opt-out requests
- Provides a privacy exposure dashboard
- Manages your personal "data broker map"
- Imports/exports encrypted backups (ZIP)
- **Runs fully offline** if desired

**No personal data ever leaves your device** except when you manually send deletion/opt-out requests to brokers.

### Cloudflare Workers (Stateless Automation)

Workers perform tasks that *don't require user PII*:

- Maintain up-to-date broker lists
- Check if broker sites are online
- Provide opt-out form templates
- Suggest re-check schedules
- Serve public metadata only

Workers compute and serve **public information only**, like:
- `brokers.json` - List of known data brokers
- Opt-out instructions and form templates
- Broker API availability tests
- Update notifications

## 🔒 Security Model

### A. Zero PII Transmission

- Cloudflare Workers **never receive PII**
- Flutter app **never transmits PII**
- All sensitive data stays **encrypted at rest** on your local device

### B. Encrypted Local Storage

- **Mobile**: SQLCipher or secure keystore
- **Desktop**: AES-256 encryption
- Optional local password or biometric lock
- Data never stored in plaintext

### C. Verification & Reproducibility

- Deterministic builds for Flutter
- GitHub Actions produce signed binaries
- Users can reproduce builds and verify checksums
- Complete source code transparency

### D. No Third-Party Tracking

- App contains **no analytics** or telemetry
- Workers log **no requests** (privacy mode enabled)
- Complete transparency in codebase

For detailed security information, see [SECURITY.md](./SECURITY.md).

## 🚀 Quick Start

### Prerequisites

- Flutter 3.x or later
- Dart 3.x or later
- (Optional) Cloudflare account for Workers deployment

### Running the Local App

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/SelfErase.git
cd SelfErase

# Navigate to Flutter app
cd flutter_app

# Get dependencies
flutter pub get

# Run on your platform
flutter run
```

### Portable Mode (Desktop)

Download a pre-built, self-contained desktop app:

1. Visit [Releases](https://github.com/OWASP-BLT/SelfErase/releases)
2. Download the ZIP for your platform
3. Extract and run - no installation needed
4. Verify the signature (optional but recommended)

### Deploying Cloudflare Workers (Optional)

```bash
# Navigate to workers directory
cd cloudflare_workers

# Install dependencies
npm install

# Deploy to your Cloudflare account
npm run deploy
```

**Note**: Workers are optional. The app works fully offline without them.

## 📖 How It Works

1. **Install the App**: Download or build the Flutter app for your device
2. **Enter Your Info Locally**: Add your personal details (name, email, addresses, etc.) - stored encrypted only on your device
3. **Scan for Exposure**: The app checks against known data brokers (using local/Workers metadata)
4. **Generate Requests**: Create opt-out/deletion requests for each broker
5. **Send Requests**: Use generated emails, forms, or automated scripts to contact brokers
6. **Track Progress**: Monitor which brokers you've contacted and their responses
7. **Re-check Periodically**: Get reminders to verify your data was actually removed

## 🗂️ Project Structure

```
SelfErase/
├── flutter_app/           # Local Flutter application
│   ├── lib/
│   │   ├── models/        # Data models (brokers, requests, etc.)
│   │   ├── services/      # Encryption, storage, networking
│   │   ├── screens/       # UI screens
│   │   └── widgets/       # Reusable UI components
│   ├── test/              # Unit and widget tests
│   └── pubspec.yaml       # Flutter dependencies
│
├── cloudflare_workers/    # Stateless edge workers
│   ├── src/
│   │   ├── brokers.ts     # Broker metadata API
│   │   ├── health.ts      # Broker health checks
│   │   └── templates.ts   # Opt-out templates
│   ├── wrangler.toml      # Cloudflare configuration
│   └── package.json       # Node dependencies
│
├── data/                  # Public broker metadata
│   ├── brokers/           # Broker definitions
│   ├── templates/         # Opt-out templates
│   └── schema.json        # Data schema
│
├── docs/                  # Documentation
│   ├── architecture.md    # Detailed architecture
│   ├── broker-guide.md    # How to add brokers
│   └── api.md             # Workers API reference
│
├── .github/
│   └── workflows/         # CI/CD workflows
│
├── README.md              # This file
├── SECURITY.md            # Security whitepaper
├── CONTRIBUTING.md        # Contribution guidelines
└── LICENSE                # AGPL-3.0 license
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Ways to Contribute

- **Add Data Brokers**: Help expand our broker database
- **Improve Templates**: Better opt-out request templates
- **Enhance Security**: Security audits and improvements
- **UI/UX**: Better user interface and experience
- **Documentation**: Clearer guides and documentation
- **Translations**: Support for more languages

## 📊 Broker Database

We maintain a curated database of data brokers with:

- Company information and contact details
- Opt-out procedures and requirements
- Form templates and example requests
- Known response times and success rates

See [data/brokers/](./data/brokers/) for the current list.

## 🛠️ Development

### Building from Source

```bash
# Flutter app
cd flutter_app
flutter build apk         # Android
flutter build ios         # iOS (macOS only)
flutter build macos       # macOS
flutter build windows     # Windows
flutter build linux       # Linux

# Cloudflare Workers
cd cloudflare_workers
npm run build
npm run test
```

### Running Tests

```bash
# Flutter tests
cd flutter_app
flutter test

# Workers tests
cd cloudflare_workers
npm test
```

## 📜 License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](./LICENSE) file for details.

## 🔐 Security

If you discover a security vulnerability, please see our [Security Policy](./SECURITY.md) for reporting instructions.

## 💡 Why SelfErase?

Most privacy tools either:
- ❌ Require you to trust them with your personal data
- ❌ Charge subscription fees for basic privacy rights
- ❌ Use opaque, closed-source methods
- ❌ Store your data on their servers

SelfErase is different:
- ✅ **Zero-trust architecture** - your data never leaves your device
- ✅ **Free and open-source** - audit the code yourself
- ✅ **Privacy by design** - impossible for us to access your data
- ✅ **User-controlled** - you own and control everything

## 🌟 Roadmap

- [x] Project architecture and design
- [ ] Core Flutter app with encrypted storage
- [ ] Basic broker database (top 50 brokers)
- [ ] Cloudflare Workers API
- [ ] Opt-out request generator
- [ ] Import/export functionality
- [ ] Automated builds and releases
- [ ] Mobile app (iOS/Android)
- [ ] Browser extension for quick scanning
- [ ] Automated submission (where possible)
- [ ] International broker support

## 📞 Support

- **Documentation**: Check our [docs/](./docs/) directory
- **Issues**: [GitHub Issues](https://github.com/OWASP-BLT/SelfErase/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OWASP-BLT/SelfErase/discussions)

## 🏆 Acknowledgments

SelfErase is part of the [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/) ecosystem.

Special thanks to:
- Privacy advocates and researchers
- Open-source contributors
- Security audit volunteers
- The OWASP community

---

**Remember**: Your privacy is a right, not a privilege. Take control with SelfErase.
