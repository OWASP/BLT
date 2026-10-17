# BLT-Vanish Guide

This document serves as an exhaustive guide for OWASP BLT-Vanish maintainers and future contributors. It details the system architecture, testing procedures, deployment workflows, and guidelines for extending core platform features post-GSoC.

---

## 1. Environment & Architecture Overview

BLT-Vanish utilizes a strict **local-first** processing model designed to protect sensitive user data. The architecture is split between a robust local client and a lightweight, privacy-preserving edge backend.

### 1.1 Client (Flutter)
The Flutter application is the brain of the operation and the sole custodian of user data.
- **State Management:** Utilizes Provider/Riverpod (depending on specific module boundaries) for reactive UI updates across the `UnifiedTriageQueue`.
- **Local Data Extraction:** Parsers extract signals from URLs (entropy, TLD checks) and emails entirely on-device.
- **Zero-Plaintext Credential Vault:** Credentials are encrypted immediately upon entry using AES-256 via the platform's native secure storage (iOS Keychain / Android Keystore). The `CredentialAnalyzer` scores password strength and reuse in memory before wiping plaintext references.
- **Unified Triage Service:** Merges localized `SecurityAlert`, `LoginAnomaly`, and `ExposureEvent` contracts into a deterministically ranked timeline prioritized by urgency and recency.

### 1.2 Backend (Cloudflare Workers)
Python-based edge workers provide non-sensitive public metadata enrichment.
- **Threat Intelligence:** The `ReputationEnrichmentService` aggregates domain reputation and acts as a rate-limiting proxy.
- **Zero-Knowledge Principle:** Workers NEVER receive PII. For instance, breach lookups only receive the first 5 characters of a SHA-1 hash (k-anonymity).

### 1.3 Strict Privacy Rules
> [!IMPORTANT]
> **No sensitive data (PII) ever leaves the device in plaintext.**
> - Telemetry services have been completely purged from the codebase. Do not reintroduce them.
> - Data breach ingestion uses strict k-anonymity models.
> - All HTTP payloads must be validated against `cloudflare_workers/python_worker/contracts.py` to ensure accidental PII leakage is structurally impossible.

---

## 2. Testing & Deployment

### 2.1 Flutter Client Verification
To verify the application integrity and ensure all privacy boundaries are intact, run the following standard Flutter pipeline:

```bash
# 1. Fetch dependencies
flutter pub get

# 2. Analyze the codebase (must return 0 errors)
flutter analyze

# 3. Execute the full regression suite
flutter test
```

**Testing Strategy:**
The regression suite contains 56 unit, widget, and integration tests.
- **Unit Tests:** Ensure deterministic behavior of `UrlSignalExtractor`, `CredentialAnalyzer`, and `RiskClassifier`.
- **Integration Tests:** Verify the end-to-end "Scan -> Triage -> Remediate" lifecycle without network dependency (mocked API calls).

### 2.2 Cloudflare Workers Backend
The backend adapters are located in the `cloudflare_workers/` directory.

**Local Testing:**
When making changes to the Python backend, ensure contract payload validation is intact using Pytest:
```bash
cd cloudflare_workers
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/
```

**Deployment:**
Deployment to edge requires the Cloudflare Wrangler CLI.
```bash
wrangler login
wrangler deploy --env production
```

---

## 3. Extending the Platform

### 3.1 Adding a New Exposure Provider
Currently, BLT-Vanish uses Have I Been Pwned (HIBP) for data breach feeds. To add a secondary provider (e.g., Firefox Monitor or a proprietary OSINT feed):

1. **Implement the Contract:** Create a new data fetching service implementing the `ExposureAdapter` Dart interface in `lib/services/`.
2. **Anonymize Data:** Ensure you strictly hash/anonymize user identifiers (email/password) *before* making the HTTP request. Use HMAC-SHA256 account keys from `exposure_identity_service.dart`.
3. **Map the Response:** Map the provider's specific JSON response schema to the canonical `ExposureEvent` object.
4. **Update the Timeline:** Inject the new adapter into `BreachMonitoringService` so it automatically populates the `UnifiedTriageQueue`.

### 3.2 Expanding the Remediation State Machine
The `PasswordRotationOrchestrator` currently relies on the user following a guided manual flow (step-by-step UI instructions). If a service provider adds an API for automated credential rotation:

1. **Create an Automated Branch:** Update the orchestrator to check if `provider.supportsAutomatedRotation` is true.
2. **Implement API Flow:** Trigger the OAuth or API flow to execute the password change on behalf of the user.
3. **Handle Rollbacks:** Ensure you handle failure/rollback states cleanly (e.g., network timeout mid-rotation) so the `RemediationTask` state machine doesn't lock up in `inProgress` indefinitely.

---

## 4. Support & Resources

- **Project Repository:** [OWASP-BLT/BLT-Vanish](https://git.owaspblt.org/BLT/BLT/tree/main/blt-vanish)
- **Core Architecture Specs:** Review the data contracts in `lib/models/security/` before proposing structural changes.
- **Issue Tracker:** Check the repository for issues tagged with `good first issue` or `help wanted` to get started.
