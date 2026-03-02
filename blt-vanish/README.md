# BLT-Vanish

**An open-source, hybrid local+edge privacy toolkit for managing and deleting personal data online.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Security: Zero PII](https://img.shields.io/badge/Security-Zero%20PII-green.svg)](./SECURITY.md)

## 🎯 Design Goal

BLT-Vanish helps individuals identify, manage, and remove their personal data from data brokers—**without ever sharing personal information with any external service.**

This is a **security-first, zero-data-retention system** where:
- ✅ All personal data stays encrypted on your local device
- ✅ No third-party servers ever see your PII
- ✅ You maintain complete ownership and control
- ✅ Works fully offline when needed
- ✅ Open-source and independently verifiable

The architecture is built around:
- ✅ **Cloudflare Workers** for automation, scanning, and re-checks
- ✅ **A local Flutter app** for **all sensitive personal data handling**
- ❌ No reliance on GitHub Pages for storing or processing personal data
- ➡️ GitHub hosts *code only*, never user data
- ⬇️ Optional "portable mode" via downloadable ZIP the user can run locally

## 🏗️ Architecture

BLT-Vanish uses a **hybrid model** that combines local security with edge automation:

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

## 💡 Why This Architecture Works

### 1. Cloudflare Workers Handle Automation

Cloudflare Workers perform tasks that *don't require user PII*, such as:

- Checking if data broker pages are online or changed
- Monitoring broker API changes
- Providing lists of brokers and opt-out methods
- Scheduling re-scan suggestions (no PII included)

Workers compute and serve only **public metadata**, like:
`brokers.json`, opt-out instructions, form templates, and availability tests.

### 2. Flutter App Handles All Personal Data

The Flutter app (runs on iOS, Android, macOS, Windows, Linux) will:

- Store **all user PII locally**, encrypted
- Construct opt-out requests
- Generate emails, form submissions, or automated scripts
- Organize the user's personal "exposure map"
- Talk to Cloudflare Workers only for public data (no PII passes through)

**No personal data ever leaves the device** except when the user manually sends deletion/opt-out requests to brokers.

### 3. Optional ZIP Download / Portable Mode

For users who want a fully offline solution, no app store, self-verifiable code, or maximum privacy, SelfErase offers a **portable ZIP download** containing a self-contained Flutter desktop app.

Users can:

- Build it from source
- Download a GitHub release
- Verify signatures
- Run locally with no installation

### 4. GitHub Hosts Only Static Files

GitHub hosts documentation, the website, the open-source code, guides, and broker metadata—no dynamic data, no PII, no user uploads. That keeps GitHub simple, safe, and fully open-source.

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

### Option 1: Web App (Easiest)

**Try BLT-Vanish directly in your browser** without installing anything:

👉 **[Launch Web App](https://owasp-blt.github.io/BLT-Vanish-Web/)**

The web app provides:
- 📝 Privacy profile creation and management
- 🔐 AES-256 encryption for profile files
- 📤 Upload/download encrypted profiles
- 🎯 Data broker information and opt-out guides
- 🛡️ All data stays in your browser - nothing sent to servers

Perfect for quick use or trying out BLT-Vanish before installing the native app.

### Option 2: Native App (Full Features)

#### Prerequisites

- Flutter 3.x or later
- Dart 3.x or later
- (Optional) Cloudflare account for Workers deployment

#### Running the Local App

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT-Vanish-Web.git
cd BLT-Vanish-Web

# Navigate to Flutter app
cd flutter_app

# Get dependencies
flutter pub get

# Run on your platform
flutter run
```

### Portable Mode (Desktop)

Download a pre-built, self-contained desktop app:

1. Visit [Releases](https://github.com/OWASP-BLT/BLT-Vanish-Web/releases)
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
BLT-Vanish-Web/
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
├── docs/                  # Documentation & GitHub Pages site
│   ├── index.html         # Web app & documentation
│   ├── app.js             # Privacy profile manager
│   ├── styles.css         # Site styling
│   ├── architecture.md    # Detailed architecture
│   ├── broker-guide.md    # How to add brokers
│   └── quick-start.md     # Getting started guide
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

## 💡 Why BLT-Vanish?

Most privacy tools either:
- ❌ Require you to trust them with your personal data
- ❌ Charge subscription fees for basic privacy rights
- ❌ Use opaque, closed-source methods
- ❌ Store your data on their servers

BLT-Vanish is different:
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
- **Issues**: [GitHub Issues](https://github.com/OWASP-BLT/BLT-Vanish-Web/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OWASP-BLT/BLT-Vanish-Web/discussions)

## 🏆 Acknowledgments

BLT-Vanish is part of the [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/) ecosystem.

Special thanks to:
- Privacy advocates and researchers
- Open-source contributors
- Security audit volunteers
- The OWASP community

---

**Remember**: Your privacy is a right, not a privilege. Take control with BLT-Vanish.
