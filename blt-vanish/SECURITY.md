# Security Whitepaper

## SelfErase: A Zero-Trust Privacy Toolkit

**Version**: 1.0  
**Last Updated**: November 2025  
**Status**: Architecture Design & Implementation

---

## Executive Summary

SelfErase is designed from the ground up with a **zero-trust, zero-retention** security model. Unlike traditional privacy services that require users to trust a third party with their personal data, SelfErase ensures that **no personal information ever leaves the user's device** unless explicitly sent by the user to a data broker for removal.

This document details the security architecture, threat model, and privacy guarantees of the SelfErase system.

---

## Core Security Principles

### 1. Zero PII Transmission

**Principle**: Personal Identifiable Information (PII) never transits through any SelfErase-controlled infrastructure.

**Implementation**:
- All personal data (names, addresses, emails, phone numbers, etc.) is stored exclusively on the user's local device
- The Flutter app never transmits PII to any server (including Cloudflare Workers)
- Cloudflare Workers operate on public metadata only (broker lists, templates, health checks)
- Communication between app and Workers involves only public, non-sensitive data

**Verification**:
- Network traffic monitoring will show zero PII in outbound requests
- Source code inspection confirms no PII serialization for remote transmission
- Workers code contains no PII processing logic

### 2. Encrypted Local Storage

**Principle**: All data at rest must be encrypted with industry-standard encryption.

**Implementation**:

#### Mobile (iOS/Android)
- **SQLCipher** for encrypted SQLite databases
- AES-256 encryption in CBC mode
- PBKDF2 key derivation (100,000+ iterations)
- Optional biometric lock (Face ID, Touch ID, fingerprint)
- Secure keystore integration (iOS Keychain, Android KeyStore)

#### Desktop (macOS/Windows/Linux)
- **AES-256-GCM** for data encryption
- **Argon2id** for password hashing
- Encrypted SQLite with custom encryption layer
- Operating system credential storage (macOS Keychain, Windows Credential Manager, Linux Secret Service)

**Encryption Flow**:
```
User Password/Biometric
    ↓
Key Derivation (PBKDF2/Argon2)
    ↓
Master Encryption Key (256-bit)
    ↓
AES-256 Encryption
    ↓
Encrypted Local Database
```

### 3. Minimal Data Collection

**Principle**: Collect only what's necessary, store only what's essential.

**Data Categories**:

| Data Type | Stored Where | Encrypted | Purpose |
|-----------|--------------|-----------|---------|
| User PII | Local device only | ✅ Yes | Generate opt-out requests |
| Broker metadata | Public GitHub/Workers | ❌ No (public data) | Broker information |
| Opt-out status | Local device only | ✅ Yes | Track progress |
| Templates | Public GitHub/Workers | ❌ No (public data) | Request generation |
| Usage analytics | **Not collected** | N/A | Privacy-first approach |

### 4. Reproducible Builds

**Principle**: Users must be able to verify that published binaries match the open-source code.

**Implementation**:
- Deterministic Flutter builds with fixed SDK versions
- GitHub Actions workflows that produce reproducible artifacts
- SHA-256 checksums for all releases
- Code signing with published certificates
- Build instructions for user verification

**Build Verification Process**:
```bash
# Clone repository at specific tag
git clone --depth 1 --branch v1.0.0 https://github.com/OWASP-BLT/SelfErase.git

# Build with fixed environment
docker run --rm -v $(pwd):/app flutter-builder:stable build apk

# Compare checksum
sha256sum build/app/outputs/flutter-apk/app-release.apk
# Should match published checksum
```

### 5. No Third-Party Tracking

**Principle**: No telemetry, analytics, or tracking of any kind.

**Implementation**:
- No Google Analytics, Firebase Analytics, or similar services
- No crash reporting services (users can optionally export logs)
- No automatic update checks that leak usage data
- Cloudflare Workers configured with minimal logging
- Open-source license prevents proprietary tracking additions

---

## Architecture Security Analysis

### Component 1: Local Flutter App

**Threat Model**:
- Physical device access by attacker
- Malware on user's device
- Memory inspection attacks
- Backup/export file interception

**Mitigations**:

1. **Encryption at Rest**
   - All PII encrypted with user-provided password/biometric
   - No plaintext data in memory longer than necessary
   - Secure memory wiping after use (where platform allows)

2. **Secure Key Management**
   - Keys derived from user credentials (never hardcoded)
   - Platform keystore integration for key storage
   - Keys never written to logs or temporary files

3. **Export Security**
   - Encrypted ZIP exports (AES-256)
   - Separate encryption password required
   - Integrity checks (HMAC) to detect tampering

4. **Code Security**
   - Regular dependency updates
   - Security linting (dart analyze, pedantic)
   - No eval() or dynamic code execution
   - Input validation on all user data

### Component 2: Cloudflare Workers

**Threat Model**:
- DDoS attacks on Workers
- Workers compromise
- Man-in-the-middle attacks
- Data injection attacks

**Mitigations**:

1. **No Sensitive Data Handling**
   - Workers never receive or process PII
   - All data served is public information
   - Compromise doesn't expose user data (none stored)

2. **HTTPS/TLS Only**
   - All Worker endpoints require HTTPS
   - TLS 1.3 with strong cipher suites
   - HSTS headers enforced

3. **Rate Limiting**
   - Cloudflare rate limiting to prevent abuse
   - No user accounts = no account takeover risk
   - Public endpoints designed for read-only access

4. **Minimal Logging**
   - Workers configured with minimal logging
   - No IP addresses or identifying information logged
   - Logs contain only public metadata requests

5. **Input Validation**
   - All API inputs validated and sanitized
   - No user-supplied code execution
   - CORS policies to prevent unauthorized origins

### Component 3: GitHub Repository

**Threat Model**:
- Supply chain attacks (malicious commits)
- Compromised dependencies
- Malicious pull requests

**Mitigations**:

1. **Code Review Process**
   - All changes reviewed by maintainers
   - Automated security scanning (Dependabot, CodeQL)
   - Signed commits encouraged

2. **Dependency Management**
   - Regular dependency audits
   - Lock files for reproducible builds
   - Automated vulnerability scanning

3. **Access Control**
   - Limited write access to repository
   - Branch protection rules
   - Required reviews for merges

---

## Data Flow Analysis

### Scenario 1: User Creates Opt-Out Request

```
1. User enters PII into Flutter app
   └─> Encrypted immediately
   └─> Stored in local SQLite (encrypted)

2. User searches for broker
   └─> App fetches broker list from Workers (HTTPS)
   └─> No PII sent in request
   └─> Public broker metadata received

3. User generates opt-out request
   └─> Template fetched from Workers (HTTPS)
   └─> PII merged with template locally
   └─> Request generated on device only

4. User sends request to broker
   └─> Email/form submitted directly to broker
   └─> No SelfErase infrastructure involved
   └─> Status saved locally (encrypted)
```

**Privacy Guarantee**: At no point does PII leave the device through SelfErase infrastructure.

### Scenario 2: User Exports Data Backup

```
1. User initiates export
   └─> Prompts for export password

2. App encrypts data
   └─> Reads encrypted local database
   └─> Re-encrypts with export password (AES-256)
   └─> Creates ZIP file with encrypted content

3. User saves ZIP file
   └─> File stored in user-chosen location
   └─> Can be transferred via any method

4. User imports on another device
   └─> Provides export password
   └─> Data decrypted and stored locally
```

**Privacy Guarantee**: Export is encrypted end-to-end. Even if intercepted, data remains protected.

### Scenario 3: Workers Health Check

```
1. Workers scheduled task runs
   └─> Reads broker list from GitHub

2. For each broker
   └─> Makes HTTP request to broker's opt-out page
   └─> Checks for 200 OK response
   └─> Updates health status

3. App polls for updates
   └─> Requests health status (no PII sent)
   └─> Receives public health data
   └─> Updates local broker information
```

**Privacy Guarantee**: Health checks involve no user data, only public broker accessibility.

---

## Threat Scenarios & Responses

### Threat 1: Malicious Insider at SelfErase

**Scenario**: A maintainer attempts to add code that exfiltrates user PII.

**Mitigations**:
- ✅ All code is open-source and reviewable
- ✅ Multiple maintainers review changes
- ✅ Users can audit source code before use
- ✅ Reproducible builds allow verification
- ✅ Even if malicious code merged, encryption keys are user-controlled

**Result**: Attack prevented by transparency and community oversight.

### Threat 2: Cloudflare Workers Compromise

**Scenario**: Attacker gains control of Workers infrastructure.

**Mitigations**:
- ✅ Workers never receive or store PII
- ✅ Compromise reveals only public broker metadata
- ✅ App functions offline without Workers
- ✅ Users can verify Worker responses against GitHub

**Result**: Limited impact. No user data exposed. Service degrades but doesn't fail.

### Threat 3: Device Theft

**Scenario**: User's device is stolen while app is unlocked.

**Mitigations**:
- ✅ App requires password/biometric re-authentication
- ✅ Data encrypted at rest even if app open
- ✅ Auto-lock timeout after inactivity
- ✅ User can remotely wipe device (OS feature)

**Result**: Data protected by encryption and authentication.

### Threat 4: Network Interception

**Scenario**: Attacker intercepts communication between app and Workers.

**Mitigations**:
- ✅ All communication over HTTPS/TLS 1.3
- ✅ Certificate pinning (optional)
- ✅ No PII transmitted to intercept
- ✅ Public data only in transit

**Result**: Even if intercepted, no sensitive data exposed.

### Threat 5: Malicious Flutter Update

**Scenario**: Attacker publishes malicious Flutter SDK update.

**Mitigations**:
- ✅ Fixed Flutter SDK version in builds
- ✅ SDK integrity verification
- ✅ Reproducible builds use specific SDK
- ✅ Community would detect and report issue

**Result**: Supply chain attack mitigated by fixed dependencies.

### Threat 6: Social Engineering

**Scenario**: Attacker tricks user into providing encryption password.

**Mitigations**:
- ⚠️ Cannot be fully prevented (user education)
- ✅ Clear warnings about password security
- ✅ Strong password requirements
- ✅ Biometric option reduces password exposure
- ✅ No legitimate reason for SelfErase to ask for password

**Result**: Requires user education and awareness.

---

## Privacy Guarantees

SelfErase provides the following guarantees:

### Strong Guarantees (Architectural)

1. **Zero PII Storage on External Servers**
   - Guaranteed by architecture
   - Workers code contains no PII handling
   - Verifiable by source code inspection

2. **Encrypted Local Storage**
   - All PII encrypted with AES-256
   - Keys derived from user credentials
   - Verifiable by code inspection

3. **No Telemetry or Tracking**
   - No analytics libraries included
   - No network calls for tracking
   - Verifiable by code inspection and network monitoring

### Best-Effort Guarantees (Operational)

4. **Reproducible Builds**
   - Best effort to maintain deterministic builds
   - May vary by platform and Flutter version
   - Users should verify on critical deployments

5. **Dependency Security**
   - Regular audits and updates
   - Automated vulnerability scanning
   - Cannot guarantee zero-day prevention

6. **Code Review**
   - All changes reviewed by maintainers
   - Community contributions reviewed
   - Human review not infallible

---

## Security Testing

### Automated Testing

- **Unit Tests**: All encryption and storage functions
- **Integration Tests**: End-to-end workflows
- **Security Linting**: dart analyze, pedantic
- **Dependency Scanning**: Dependabot, Snyk
- **Static Analysis**: CodeQL

### Manual Testing

- **Code Review**: Human review of all changes
- **Penetration Testing**: Periodic security audits
- **Network Analysis**: Traffic inspection for PII leaks
- **Platform Security**: OS-level security features

### Community Security

- **Bug Bounty**: Responsible disclosure encouraged
- **Public Audits**: Third-party security audits welcomed
- **Transparency Reports**: Regular security status updates

---

## Compliance & Standards

### Privacy Regulations

SelfErase helps users exercise rights under:
- **GDPR** (EU): Right to erasure, data portability
- **CCPA** (California): Right to deletion, opt-out
- **PIPEDA** (Canada): Right to deletion
- **LGPD** (Brazil): Right to deletion

### Security Standards

SelfErase follows:
- **OWASP Mobile Security**: Top 10 mitigations
- **NIST Cybersecurity Framework**: Best practices
- **CIS Controls**: Security baseline implementation

---

## Incident Response

### Vulnerability Disclosure

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. Email security contact: [To be configured]
3. Include detailed description and reproduction steps
4. Allow 90 days for patch before public disclosure
5. We'll credit you in security advisories (if desired)

### Incident Response Process

1. **Detection**: Vulnerability reported or discovered
2. **Assessment**: Severity and impact evaluation
3. **Mitigation**: Patch development and testing
4. **Release**: Security update published
5. **Disclosure**: Public advisory with details
6. **Review**: Post-mortem and improvements

---

## Security Roadmap

### Completed
- [x] Zero-PII architecture design
- [x] Threat model documentation
- [x] Encryption strategy

### In Progress
- [ ] Implementation of encrypted storage
- [ ] Security audit of core components
- [ ] Reproducible build system

### Planned
- [ ] Third-party security audit
- [ ] Bug bounty program
- [ ] Formal security certifications
- [ ] Hardware security key support
- [ ] Advanced threat protection

---

## Conclusion

SelfErase's security model is based on a simple principle: **we can't compromise data we never have access to**.

By keeping all personal data encrypted on user devices and using external services only for public metadata, we eliminate entire categories of security risks.

Users don't have to trust us—they can verify our claims through:
- Open-source code inspection
- Network traffic analysis  
- Reproducible build verification
- Community security audits

**Privacy is not a promise—it's an architecture.**

---

## Contact

- **Security Issues**: [Create private security advisory](https://github.com/OWASP-BLT/SelfErase/security/advisories/new)
- **General Security Questions**: [GitHub Discussions](https://github.com/OWASP-BLT/SelfErase/discussions)
- **Documentation**: [docs/security/](./docs/security/)

---

**Version History**:
- v1.0 (Nov 2025): Initial security whitepaper
