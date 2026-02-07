# NetGuardian: Zero-Trust Encrypted Web Scanner & Triage-Lite Platform (2026 — 350hr)

## Project Overview
BLT-NetGuardian is a production-ready, privacy-preserving security scanning workflow that finds verifiable web vulnerabilities and safely hands them off inside BLT with minimal reviewer effort. It ships end-to-end encrypted ingestion (Zero Trust), a real detection pack (web vulns + Semgrep SAST), a volunteer CLI client for distributed scanning, a normalized finding schema with basic validation/dedup, disclosure helpers (security.txt), and a professional remediation report (CSV/PDF) — scoped to 350 hours.

## Core Objectives
- Replace demo/stub scanning with real, reproducible vulnerability detection (XSS/SQLi/CSRF/headers + Semgrep starter subset).
- Keep sensitive evidence safe by default via Zero-Trust encrypted ingestion (signed + timestamped submissions; nonce replay protection).
- Reduce reviewer toil with a common finding schema, basic validation, dedup fingerprints, and a triage-lite UI:
  - list + filters
  - evidence viewer
  - client-side decrypt
  - “Convert to Issue”
- Improve accuracy over time via curated evaluation targets, spot checks, and rule tuning to reduce false positives/negatives.
- Improve responsible disclosure workflows with security.txt detection and contact hints.
- Provide professional exports (formula-safe CSV + PDF remediation report) for organizations.

## Timeline (4 Phases × 4 Weeks, ~350 hours)

### Phase 1 (Weeks 1–4 | ~90 hours) — Zero Trust + Detection MVP + Common Schema
- Zero Trust ingestion
  - Implement `ztr-finding-1` encrypted envelope (E2E), signed + timestamped submission
  - Nonce replay protection (cache) + audit stubs for critical events
  - Organization key distribution + rotation endpoints
- Detection MVP
  - Web vuln starter pack: XSS, SQLi, CSRF, security headers
  - Semgrep SAST subset for Python/JS with initial severity tuning
- Normalized findings + triage-lite (MVP)
  - Common JSON schema (idempotent IDs, severity, evidence, target URL)
  - Triage-lite UI: list findings, basic filters, evidence viewer, client-side decrypt, “Convert to Issue”
- Acceptance
  - Encrypted findings flow from NetGuardian → BLT; authorized org user decrypts and converts to issue
  - At least 1–2 rules per category produce verifiable evidence

### Phase 2 (Weeks 5–8 | ~110 hours) — Volunteer CLI + Validation/Dedup + UX Refinements
- Volunteer CLI client
  - Fetch → execute → submit tasks
  - Local resource caps (timeouts, concurrency, size limits), opt-in target controls
- Validation + dedup (basic)
  - Fingerprints: (rule + URL + selector); idempotent submissions
  - Minimal confidence scoring + FP checklist UI
- Semgrep expansion & noise reduction
  - Expand coverage thoughtfully; suppress noisy rules; tune severities
- Triage-lite UX improvements
  - Filters: severity/rule/domain/date; improved evidence viewer
  - “Request more info” templates for structured follow-ups
- Acceptance
  - CLI completes end-to-end tasks reliably
  - Dedup removes repeats on re-scan; triage queue becomes cleaner and more actionable

### Phase 3 (Weeks 9–12 | ~90 hours) — Quality, Accuracy & Light Resilience
- Accuracy sampling + tuning
  - Curated targets; weekly spot-checks; iterate on rules from FP/FN learnings
- Light consensus for critical findings
  - Require reconfirmation evidence for critical severity before conversion prompt
  - Boost confidence score when reconfirmed
- Minimal resilience controls
  - Batch ingestion, per-org rate limits/quotas, basic back-pressure
- Remediation groundwork
  - Shared markdown remediation fragments per rule type (with OWASP links)
- Acceptance
  - Measurable precision improvement on curated set
  - Critical findings include reconfirmation evidence; ingestion steady under moderate load

### Phase 4 (Weeks 13–16 | ~60 hours) — Disclosure Helpers + Pro Report + Pilot
- Disclosure helpers
  - Detect `security.txt`; surface contact hints during “Convert to Issue”
- Professional remediation report
  - One-off export: formula-safe CSV + PDF with findings, severity, affected URLs, remediation notes
- Pilot & release
  - Pilot with 1–2 orgs; polish; docs (user/admin/setup/contrib); tag v1.0
- Acceptance
  - Pilot orgs export report and complete disclosure flow using security.txt hints
  - v1.0 sign-off with working encrypted scanning → triage → issue conversion

## Benefits
- Credible scanning foundation: real detections + verifiable evidence (not demo output).
- Privacy-preserving by default: sensitive evidence stays encrypted end-to-end; decrypt happens client-side for authorized users.
- Lower reviewer workload: normalized findings, dedup, and triage-lite handoff reduce time spent sorting noise.
- Community-powered scaling: volunteer CLI enables distributed scanning without centralizing sensitive evidence.
- Better disclosure hygiene: security.txt hints streamline responsible outreach.
- Practical outputs for orgs: professional CSV/PDF remediation report supports remediation tracking.
