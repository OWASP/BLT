# SelfErase Architecture

## Overview

SelfErase uses a **hybrid local+edge architecture** designed for maximum privacy and zero trust.

## Core Principles

1. **Zero PII Transmission**: Personal data never leaves the user's device
2. **Encryption at Rest**: All local data encrypted with AES-256
3. **Stateless Edge**: Workers serve only public metadata
4. **Offline-First**: Full functionality without internet
5. **Open Source**: Complete transparency and auditability

## Components

### 1. Local Flutter App

**Purpose**: Handle all sensitive personal data

**Responsibilities**:
- Store user PII (encrypted)
- Generate opt-out requests
- Track request status
- Provide user dashboard
- Import/export encrypted backups

**Technology**:
- Flutter 3.x (cross-platform)
- SQLCipher (encrypted database)
- AES-256-GCM encryption
- Platform secure storage (Keychain/KeyStore)

**Data Flow**:
```
User Input → Encryption → Local Storage
           ↓
    Local Processing Only
           ↓
    Opt-Out Request → Direct to Broker
```

### 2. Cloudflare Workers

**Purpose**: Serve public broker metadata

**Responsibilities**:
- Maintain broker database
- Check broker site health
- Provide opt-out templates
- Serve API endpoints

**Technology**:
- Cloudflare Workers (edge functions)
- TypeScript
- No database (stateless or KV for caching)

**Data Flow**:
```
GitHub → Workers → App
(public data only)
```

### 3. GitHub Repository

**Purpose**: Store public data and code

**Responsibilities**:
- Host source code
- Store broker metadata
- Provide documentation
- CI/CD for builds

**Data Stored**:
- Source code
- Broker definitions (public)
- Opt-out templates (public)
- Documentation

## Security Model

### Threat Model

**Threats Considered**:
1. Device theft/loss
2. Network interception
3. Malicious Workers
4. Compromised brokers
5. Supply chain attacks

**Mitigations**:
1. Local encryption + biometric lock
2. HTTPS + no PII transmission
3. Workers handle no PII
4. User controls all broker communication
5. Reproducible builds + signatures

### Data Classification

| Data Type | Location | Encrypted | Transmitted |
|-----------|----------|-----------|-------------|
| User PII | Local device only | ✅ Yes | ❌ No* |
| Broker metadata | GitHub/Workers | ❌ No (public) | ✅ Yes |
| Templates | GitHub/Workers | ❌ No (public) | ✅ Yes |
| Request status | Local device only | ✅ Yes | ❌ No |

*User may manually send PII directly to brokers via email/forms

### Encryption Details

**At Rest**:
- Algorithm: AES-256-GCM
- Key derivation: PBKDF2 (100k+ iterations) or Argon2id
- Key storage: Platform secure storage
- IV: Random per encryption operation

**In Transit**:
- HTTPS/TLS 1.3 for all network calls
- Certificate pinning (optional)
- No PII in requests to Workers

## Workflows

### Initial Setup

```
1. User installs app
2. App generates encryption key
3. User creates profile (encrypted locally)
4. App fetches broker list from Workers (optional)
```

### Creating Opt-Out Request

```
1. User searches brokers (local or via Workers)
2. User selects broker
3. App fetches template (from Workers or cache)
4. App merges user data + template (locally)
5. User reviews and sends request directly to broker
6. App tracks status (encrypted locally)
```

### Health Checks

```
1. Workers periodically check broker URLs
2. Workers update health status
3. App fetches health data (when online)
4. User sees broker availability
```

### Backup/Export

```
1. User initiates export
2. App encrypts all data with export key
3. ZIP file created (encrypted)
4. User saves to preferred location
5. User can import on another device
```

## Deployment

### Flutter App

**Platforms**:
- iOS (App Store)
- Android (Google Play)
- macOS (direct download)
- Windows (direct download)
- Linux (direct download)

**Distribution**:
- App stores (mobile)
- GitHub Releases (desktop)
- Portable ZIP (all platforms)

### Cloudflare Workers

**Deployment**:
```bash
cd cloudflare_workers
npm run deploy
```

**Endpoints**:
- Production: `https://selferase.workers.dev`
- Custom domain: `https://api.selferase.org` (optional)

### GitHub Pages

**Content**:
- Documentation
- Project website
- Broker database (JSON)

## Scalability

### App
- Local storage scales to thousands of brokers
- Lightweight (<50MB installed)
- Works fully offline

### Workers
- Cloudflare global edge network
- Auto-scales to demand
- <10ms latency worldwide

### Data
- Broker database: JSON files on GitHub
- Can scale to 10,000+ brokers
- Community-contributed updates

## Future Enhancements

1. **Browser Extension**: Quick scan from any page
2. **Automated Submission**: Where legally possible
3. **International Support**: More countries and languages
4. **Hardware Keys**: YubiKey/FIDO2 support
5. **Blockchain Verification**: Proof of deletion requests

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for architecture contribution guidelines.
