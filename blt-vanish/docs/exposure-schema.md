# Exposure Intelligence Schema & Architecture

This document defines the architecture and privacy boundaries for the Exposure Intelligence module (Phase 3).

## Data Schema: `ExposureEvent`

All incoming data from various providers (e.g., HIBP) is mapped into a normalized schema to ensure cross-provider compatibility and a unified timeline UI.

```dart
class ExposureEvent {
  final String source;        // Provider identifier, e.g., 'HIBP: 000webhost'
  final DateTime occurredAt;  // Best-effort timestamp of the breach
  final String urgency;       // 'low', 'medium', 'high', 'critical'
  final double confidence;    // 0.0 to 1.0
  final String accountHash;   // HMAC-SHA256 representation of the target account
}
```

### Urgency Mapping
- **Critical/High**: Breaches containing Passwords, Security Questions, or SSNs.
- **Medium**: Breaches containing Emails, Phone Numbers, or Physical Addresses.
- **Low**: Breaches containing general profile data (e.g., Job Titles, Genders).

## Privacy & Identity Management

A core tenet of BLT-Vanish is that **no plaintext PII leaves the device**. 

### Password k-Anonymity
When checking for compromised passwords, the application uses the **k-Anonymity model**. 
1. The password is hashed locally using SHA-1.
2. Only the **first 5 characters** of the hash are transmitted to the external API (e.g., HIBP).
3. The API returns a list of matching hash suffixes.
4. The application compares the remaining suffix locally.

### Email Hashing (HMAC-SHA256)
Plaintext emails are never persisted in local storage or transmitted in plain text unless strictly required by a provider's secure endpoint (which is actively avoided).
- `ExposureIdentityService` uses an app-specific cryptographic secret to generate HMAC-SHA256 hashes of the user's email addresses.
- The normalized `ExposureEvent` only stores this `accountHash` for linking events back to the user without exposing the email itself.

## Breach Monitoring Workflow

The `BreachMonitoringService` orchestrates the fetching of new exposure events.

1. **Triggers**:
   - **App Launch**: A background sync is triggered shortly after the app opens.
   - **Periodic Background Task**: Hooks are provided (intended for `workmanager` or equivalent) to run a daily silent sync.
   - **Manual Request**: A user can force a refresh from the Security Center UI.
2. **Deduplication**: Incoming events are checked against the local cache. Exact matches (same source, date, and accountHash) are discarded to prevent timeline clutter.
3. **Notifications**: If a newly ingested event maps to a `high` or `critical` urgency, the service triggers a local push notification immediately.

## Fallback and Degraded States

If the exposure feed (e.g., HIBP) is unreachable due to rate limits or offline scenarios, the Security Center UI falls back to a **Degraded State**. It will display:
- A warning banner indicating the feed is unavailable.
- The timestamp of the `lastSyncTime`.
- A manual retry button. 

## Post-GSoC Extensions

The `ExposureAdapter` interface is designed to be extensible. Post-GSoC, additional adapters (e.g., for specific dark web monitoring APIs or custom threat intelligence feeds) can be plugged in by implementing the `checkEmailExposure` and `checkPasswordExposure` methods, mapping their unique payloads to the unified `ExposureEvent`.
