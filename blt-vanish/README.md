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
│   │   ├── index.py       # Main router and handlers
│   │   ├── brokers.py     # Broker metadata API
│   │   ├── health.py      # Broker health checks
│   │   ├── responses.py   # Shared HTTP response helpers
│   │   └── templates.py   # Opt-out templates
│   ├── wrangler.toml      # Cloudflare configuration
│   └── package.json       # Wrangler deployment launcher
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


Current Implementation Overview
Users can submit URLs and keywords to monitor
A daily command checks if keywords appear on specified websites
Users receive email notifications when status changes (keyword appears/disappears)
Basic UI for submission and monitoring
Improvement Recommendations
1. Enhanced Detection Capabilities
Implement NLP/ML to detect personal information instead of just keywords
Add pattern matching for common PII (emails, phone numbers, addresses, etc.)
Support regex patterns for more flexible matching
Add context-aware detection to reduce false positives
2. Automated Takedown Assistance
Generate pre-formatted takedown request templates for different platforms
Integrate with common platforms' APIs for automated takedown requests
Track takedown request status and follow-ups
Provide legal resources and guidance for different jurisdictions
3. Improved User Experience
Redesign dashboard with status summaries and visual indicators
Add detailed history tracking of each monitoring request
Implement severity ratings for detected information
Add bulk operations for managing multiple monitors
4. Advanced Monitoring Features
Scheduled scans with configurable frequency
Support for authenticated website monitoring (with secure credential storage)
Screenshot capture for evidence preservation
Diff highlighting to show changes between scans
5. Extended Platform Coverage
Add support for social media platforms
Monitor search engine results
Check dark web exposure
Monitor data breach databases
6. Privacy and Security Enhancements
End-to-end encryption of sensitive monitoring data
Rate limiting to prevent abuse
Improve authentication and authorization
Add audit logging for compliance
7. Integration and Reporting
Export capabilities for documentation
Integration with legal case management systems
Comprehensive reporting with trends and statistics
API for third-party service integration

**Remember**: Your privacy is a right, not a privilege. Take control with BLT-Vanish.

## BLT-Vanish Web — Project Roadmap (GSoC 2026)

This roadmap maps the Community Bonding period and a 12-week development cadence across three phases (Phase 1–3), plus CI, testing, documentation, and final handover. Each phase lists weekly goals, key deliverables, acceptance criteria, and mentor checkpoints.

---

## Timeline (high level)

- Community Bonding: May 1 — May 24, 2026
- Coding Period: May 25 — August 17, 2026 (12 weeks)
  - Phase 1 (Weeks 1–4): Foundational risk engine, phishing MVP, Security Center UX
  - Phase 2 (Weeks 5–8): Credential hygiene, remediation orchestration, unified triage
  - Phase 3 (Weeks 9–12): Exposure ingestion, login-anomaly detection, release hardening

---

## Milestones & Week-by-week Plan

### Community Bonding (3 weeks)

- Align architecture and non-PII boundaries
- Finalize API contracts and reason-code taxonomy
- Agree on mentor cadence, acceptance tests, and demo script

### Phase 1 — Foundational Risk Engine & Phishing MVP (Weeks 1–4)

- Week 1: Contracts & scaffolding
  - Add `docs/security-contracts.md` (SecurityAlert, RiskAssessment, RemediationAction)
  - Add Worker `contracts.py` validators and contract tests (Python/Dart)
  - Scoring service skeleton in `flutter_app/lib/services/security_risk_service.dart`
  - Deliverable: frozen v1 contract doc + CI contract tests

- Week 2: Feature extraction & enrichment
  - Implement `UrlSignalExtractor` and deterministic local features
  - Worker enrichment adapter with 1500ms timeout + retry policy
  - `RiskAssessmentBuilder` to combine local+enrichment signals
  - Deliverable: extractor + enrichment adapter + fixture tests

- Week 3: Security Center scan flow & UI
  - Implement `SecurityCenterScreen`, loading/error/offline states
  - Integrate extractors, enrichment, and assessment into scan flow
  - Render severity cards, reason-code chips, remediation CTAs
  - Deliverable: end-to-end scan flow + integration tests

- Week 4: Calibration & hardening
  - Implement `RiskClassifier`, false-positive gates, and threshold tuning
  - Regression test suite with labeled URLs and metrics baseline
  - Deliverable: calibrated classifier + `docs/phase-1-benchmark.md`

### Phase 2 — Credential Hygiene & Remediation (Weeks 5–8)

- Week 5: Credential analyzer

  - Implement `CredentialAnalyzer` (strength, reuse likelihood, exposure posture)
  - Hash-only snapshots for persistence (no plaintext)
  - Deliverable: deterministic credential scoring + unit tests

- Week 6: Remediation planner & state machine
  - Implement `RemediationTask` state machine and `RemediationPlanner`
  - Midterm metrics aggregator and automated test harness
  - Deliverable: remediation lifecycle + midterm report

- Week 7: Unified triage
  - `UnifiedTriageService` to rank phishing + credential items
  - Timeline UI with global filters and quick actions
  - Deliverable: unified queue + E2E tests

- Week 8: Stabilize & package Phase 2
  - Close defects, performance hardening, and gating CI checks
  - Produce Phase 2 artifacts and demo branch

### Phase 3 — Exposure Intelligence, Login Anomaly, Hardening (Weeks 9–12)

- Week 9: Exposure ingestion
  - Build breach/dark-web adapters using privacy-safe identifiers
  - Timeline ingestion; normalization into RiskAssessment model

- Week 10: Login anomaly detection
  - Suspicious-login correlation engine and provider adapters
  - Alert-to-remediation pathways for takeover prevention

- Week 11: Integration & regression
  - Merge all modules into single prioritized risk timeline
  - Run full regression suites and performance budgets

- Week 12: Release hardening & handover
  - Final documentation, demo scripts, and release artifacts
  - Mentor walkthrough and handover package

---

## CI, Testing & Performance Gates

- CI gates per phase (`ci/phase1-gate.yml`, `ci/phase2-gate.yml`, `ci/phase3-gate.yml`)
  - Required checks: static analyze, unit tests, integration tests, performance budget
- Benchmarks: precision/recall for phishing detection, scan latency, memory and battery impact

---

## Documentation & Demos

- Contract docs: `docs/security-contracts.md`
- UI spec: `docs/security-center-ui-spec.md`
- Benchmarks & calibration: `docs/phase-1-benchmark.md`, `docs/phase-2-performance.md`
- Midterm and final reports: `docs/midterm-evaluation.md`, `docs/final-handover.md`

---

## Overview of Layers, Workflows, and UI Component Matrix

### I. Detailed Layered Architecture & Processing Workflows

The BLT-Vanish Web platform operates on a **zero-trust, zero-retention hybrid architecture** that cleanly splits execution responsibilities across three logical environments. This division ensures that no personally identifiable information (PII) or unencrypted credentials ever touch external infrastructure.

```txt
+-------------------------------------------------------------------------+
|                        LOCAL LAYER (Flutter App)                        |
|   - Inspects Raw PII   - Local Feature Extraction  - Risk Computation   |
+-----------------------------------+-------------------------------------+
|
Requests Public | Responds with
Metadata Only   | Clean JSON DTOs
v
+-------------------------------------------------------------------------+
|                       EDGE LAYER (Cloudflare Workers)                   |
|   - Domain Reputation  - Broker Data Endpoints     - Template Servers   |
+-----------------------------------+-------------------------------------+
|
v
+-------------------------------------------------------------------------+
|                  BACKEND THREAT INTELLIGENCE LAYER                      |
|   - Rate Limiting      - Secure Alert Routing      - Observability      |
+-------------------------------------------------------------------------+
```

### 1. The Local Layer (Flutter Application Client)

The local client executes all computations involving raw user identity context.

* **Workflow Execution:** When an asset (URL, message string, or credential pair) is triggered for evaluation, the local layer captures the telemetry input, processes it safely inside volatile memory, and maps it directly to local feature extractors.

* **Security Isolations:** This layer runs completely offline-first if necessary, encrypting local state snapshots with platform-native keystores (iOS Keychain, Android KeyStore, or Windows Credential Manager).

* **Contract Responsibility:** It enforces schema parsing gates using typed factory models (`SecurityAlert.fromJson`), throwing immediate exceptions if data structures arriving across boundaries are malformed or out of bounds.

### 2. The Edge Layer (Cloudflare Workers Runtime)

The edge network operates as a fast, stateless public metadata distributor.

* **Workflow Execution:** Workers respond to lookups sent by the client via endpoints like `/api/brokers`, `/api/health/:id`, `/api/reputation`, and `/api/templates/:templateId`. It handles data matching requests within a strict **1500ms timeout budget**.

* **Security Isolations:** Workers are designed and implemented never to receive, process, or log user PII — enforced by only accepting anonymized public metadata as inputs.

* **Contract Responsibility:** The edge layer utilizes Python type guards (`isSecurityAlertDTO`) to perform strict symmetric schema validation on requests and responses before passing data payloads down to the client device.

### 3. The Backend Threat Intelligence Layer

This production support tier acts as a control plane for handling infrastructure traffic rules and routing integrations securely.

* **Workflow Execution:** It handles incoming automated provider alert feeds, normalizes security warning payloads into unified events, and pushes alert context directly to the client synchronization pipeline.

* **Security Isolations:** Employs route-level rate limiting, zero-knowledge encryption pipelines, and privacy-first log redaction middleware to guarantee metadata cannot be reverse-engineered to identify a user.

---

## II. End-to-End Core Threat Workflows

### 1. Real-Time Phishing & Malicious-Link Processing Pipeline

This workflow inspects raw, untrusted links submitted by the user through manual pasting or OS sharing mechanisms.

```txt
[Input Pasted] ---> (UrlSignalExtractor) ---> [Call Edge API] ---> (RiskAssessmentBuilder) ---> (RiskClassifier) ---> [UI Draw]

```

* **Step A (Local Extraction):** The link is sent to the `UrlSignalExtractor`. It performs on-device analysis to calculate Shannon entropy scores and evaluate malicious lexical indicators:

  * `entropy`: Normalized string randomness evaluation.
  
  * `suspicious_tokens`: Checks for string sequences matching target phrases like `verify`, `secure`, or `login`.
  
  * `risky_tld`: Matches against high-frequency scam extensions like `.zip`, `.click`, `.top`, or `.xyz`.

* **Step B (Edge Enrichment):** The app strips all unique parameter query context from the domain to mask individual actions and submits the clean host string to the Cloudflare Worker `/api/reputation` endpoint to pull public domain health metrics.

* **Step C (Score Composition):** The client merges local heuristics and public intelligence values using the foundational Phase 1 risk composition model:

    $$Risk = w_1U + w_2M + w_3R$$
    
    *(Where $U$ represents the URL lexical risk indicators, $M$ represents message indicators, and $R$ represents reputation intelligence signals. Note: The weights $w_1, w_2,$ and $w_3$ are starting placeholder configurations subject to precision and false-positive calibration during Phase 1 implementation — see `docs/phase-1-benchmark.md` for current calibration dataset trends)*.

* **Step D (Severity Mapping):** The computed score is passed through a deterministic threshold classifier to map it directly into standardized severity classes:

    $$severity(Risk)=\begin{cases} critical, & Risk \ge 0.85 \\ high, & 0.65 \le Risk < 0.85 \\ medium, & 0.40 \le Risk < 0.65 \\ low, & Risk < 0.40 \end{cases}$$

### 2. Zero-Plaintext Credential Hygiene & Tracking Lifecycle

This workflow tracks internal credential safety and orchestrates password strengthening tasks locally.

* **Step A (Ingestion & Hash Derivative Processing):** The user saves or imports credential references. The `CredentialVaultService` immediately processes the plaintext inside runtime-volatile memory, computes entropy and character variance snapshots, hashes the material for pattern matching, and securely clears raw strings from device memory.

* **Step B (Local Scoring):** The `CredentialAnalyzer` passes the mathematical properties of the credential through the baseline scoring model:
    $$CredentialRisk = 0.35S + 0.40R + 0.25E$$

    *(Where $S$ represents strength weakness, $R$ represents reuse count likelihood, and $E$ represents exposure posture context. Note: The weights are starting placeholder configurations subject to calibration during Phase 2 implementation)*.

* **Step C (Remediation Checklist Injection):** If the risk score crosses designated limits, a warning is triggered. The `RemediationPlanner` creates a corresponding tracking container called a `RemediationTask` with an initial state marked as `notStarted`.

* **Step D (Orchestration & State Change Monitoring):** When the user executes a task, the `PasswordRotationOrchestrator` runs state rules to guide the change lifecycle (`requested -> applied -> verified -> completed`). Upon hitting a verified status, the task transitions to `completed`, safely updating the encrypted local timeline view.

### 3. Privacy-Safe Breach/Dark Web Exposure Pipeline

This service monitors historical data exposures using privacy-safe tracking keys.

* **Step A (Identity Anonymization):** The application applies a local cryptographic salt to user email identifiers and computes a non-reversible hash: `accountHash = sha256(emailLowercase + salt)`.

* **Step B (K-Anonymity External Check):** The system passes anonymized search fragments to the external feed (such as Have I Been Pwned). The edge infrastructure queries breach databases using prefix lookups, ensuring your cleartext query credentials never traverse external paths.

* **Step C (Normalization):** Incoming exposure alerts are parsed by the client's `ExposureAdapter` and normalized directly into uniform `ExposureEvent` models containing standardized urgency, recency, and impact indicators.

### 4. Suspicious Login Correlation & Threat Escalation

This backend-to-client intelligence loop processes account takeover risk profiles.

* **Step A (Context Vector Evaluation):** Whenever an account event metadata notification is ingested, the system reads specific environmental check properties, passing flags such as `newGeo`, `newDevice`, `oddHour`, and `priorPhishingAlert` through an anomaly engine.

* **Step B (Correlation Calculation):** The engine tracks environmental variations, adding a priority escalation value using the Phase 3 prioritization matrix:
    $$Priority = 0.45 \cdot Severity + 0.30 \cdot Confidence + 0.25 \cdot ActionUrgency$$

* **Step C (Playbook Selection & Local Escalation):** If a high priority score is confirmed, a specific playbook is selected (e.g., *Session Revoke / MFA Reset*). If the task remains ignored by the user over several days, the local state engine triggers internal escalation rules, updating the active tracking value from standard priority up to critical levels (`escalationLevel 1` -> `escalationLevel 2`).

---

## III. UI Component Matrix & Cross-Layer Interactivity

The application UI acts as a highly scannable, componentized presentation layer that directly binds interactive controls to our underlying asynchronous security state engines.

| UI Component File Name | Component Functional Goal | Linked Internal Workflows | Edge / Backend Interactions |
| :--- | :--- | :--- | :--- |
| **`security_center_screen.dart`** | Acts as the primary interactive entry view for link checks, manual scanning input boxes, and real-time scanning action buttons. | • Real-Time Phishing Scanning Workflow<br>• Malicious Link Classification Pipeline | Calls Cloudflare Worker endpoints (`/api/reputation`) using a strict 1500ms timeout threshold, returning fallback mock structures if offline. |
| **`severity_cards_widget.dart`** | Displays large, color-coded dashboard indicators matching computed risk tiers (`critical` = Red, `high` = Orange, `medium` = Yellow, `low` = Green). | • Deterministic Threat Severity Mapping<br>• Phishing Analysis Presentation Flow | None (Pure client rendering block driven by hydrated `SecurityAlert` payloads). |
| **`reason_code_chips.dart`** | Translates abstract backend technical identifiers into descriptive, scannable chips via translation wrappers (e.g., converts `SUSPICIOUS_TLD` text dynamically). | • System Risk Explainability Framework<br>• Threat Factor Weight Presentation | None (Renders data derived directly from the immutable `reasonCodes` list within the local data layer). |
| **`remediation_cta_button.dart`** | Displays clear contextual call-to-action controls based on threat types, mapping direct one-click routes to resolution workflows. | • Remediation Task Lifecycle Initiation<br>• Password Rotation Routine Trigger | Triggers local client operations; may request updated opt-out instruction payloads from `/api/templates`. |
| **`unified_triage_timeline.dart`** | Renders a unified chronological activity board merging cross-module risks sorted by global urgency parameters. | • Unified Triage Evaluation Engine<br>• Equal-Score Source Priority Tie-Breaking | Consumes compressed local tracking snapshots; displays push notifications pushed from the backend context processor. |
| **`exposure_timeline_view.dart`** | Displays dark-web and public breach exposure logs grouped cleanly by recency and threat weight constraints. | • Privacy-Safe Breach Ingestion Pipeline<br>• Account Identity Hashing Sequence | Displays last-sync indicators; offers manual sync triggers that run anonymized, prefix-hashed network discovery lookup requests. |
| **`playbook_action_card.dart`** | Renders an overlay view containing guided instructions for account security tasks, session cancellations, and lock procedures. | • Takeover Prevention Action Playbook Selection<br>• Account Hardening Progress Sync | Monitors state changes inside the `RemediationTask` engine, securely committing local snapshot state updates to the app database. |

---
