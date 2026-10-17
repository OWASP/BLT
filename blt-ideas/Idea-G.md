# NetGuardian: Zero-Trust Encrypted Web Scanner & CVE-Aware Triage Platform (2026 — 350hr)

## Idea Overview
BLT-NetGuardian is a production-ready, privacy-preserving security scanning workflow that finds verifiable web vulnerabilities, **enriches them with CVE intelligence**, and safely hands them off inside BLT with minimal reviewer effort. It ships end-to-end encrypted ingestion (Zero Trust), a real detection pack (web vulns + Semgrep SAST), a normalized finding schema with basic validation/dedup, a CVE intelligence layer (reusing BLT’s CVE cache/search), disclosure helpers (security.txt), and a professional remediation report (CSV/PDF) — scoped to 350 hours.

> NetGuardian in this idea assumes BLT-managed scanning runners by default. A volunteer/distributed CLI client is a natural future extension, but not required to get a strong v1 within 350h.

## Core Objectives
- Replace demo/stub scanning with real, reproducible vulnerability detection (XSS/SQLi/CSRF/headers + Semgrep starter subset).
- Keep sensitive evidence safe by default via Zero-Trust encrypted ingestion (signed + timestamped submissions; nonce replay protection).
- Reduce reviewer toil with a common finding schema, basic validation, dedup fingerprints, and a triage-lite UI:
  - list + filters
  - evidence viewer
  - client-side decrypt
  - “Convert to Issue”
- **Make findings CVE-aware by design via a CVE Intelligence layer**:
  - reuse BLT’s CVE caching/search work (from the CVE integration already merged into BLT) to auto-annotate findings with `cve_id` + `cve_score` where possible
  - allow CVE-based filters and “related CVEs” views in the triage UI
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

- **CVE Intelligence layer (hooked into MVP)**  
  - Wire findings → BLT’s CVE cache/search (existing CVE integration work in BLT)  
  - When a rule emits a known CVE ID, auto-populate `cve_id` and `cve_score` on the finding/Issue model  
  - Add basic `cve_id` and `cve_score` columns to the triage list view

- Acceptance  
  - Encrypted findings flow from NetGuardian → BLT; authorized org user decrypts and converts to issue  
  - At least 1–2 rules per category produce verifiable evidence  
  - Findings with CVEs show `cve_id` and `cve_score` using the shared CVE cache

### Phase 2 (Weeks 5–8 | ~110 hours) — Validation/Dedup + CVE-Aware Triage UX

- Validation + dedup (basic)  
  - Fingerprints: (rule + URL + selector); idempotent submissions  
  - Minimal confidence scoring + FP checklist UI

- Semgrep expansion & noise reduction  
  - Expand coverage thoughtfully; suppress noisy rules; tune severities

- **CVE-aware triage UX**  
  - Filters: severity/rule/domain/date + **`cve_id`, `cve_score_min`, `cve_score_max`** (via existing CVE filter APIs)  
  - “Related CVEs” panel for a target/domain using the BLT CVE index  
  - Reuse CVE autocomplete in “Convert to Issue” and manual override UX

- Triage-lite UX improvements  
  - Improved evidence viewer  
  - “Request more info” templates for structured follow-ups

- Acceptance  
  - Dedup removes repeats on re-scan; triage queue becomes cleaner and more actionable  
  - Triagers can filter and sort by CVE metadata and see related CVEs without leaving NetGuardian

### Phase 3 (Weeks 9–12 | ~90 hours) — Accuracy, CVE-Driven Insights & Light Resilience

- Accuracy sampling + tuning  
  - Curated targets; weekly spot-checks; iterate on rules from FP/FN learnings

- Light consensus for critical findings  
  - Require reconfirmation evidence for critical severity before conversion prompt  
  - Boost confidence score when reconfirmed

- Minimal resilience controls  
  - Batch ingestion, per-org rate limits/quotas, basic back-pressure

- Remediation groundwork  
  - Shared markdown remediation fragments per rule type (with OWASP links)  
  - Use CVE metadata (where present) to link to relevant advisories and OWASP resources

- Acceptance  
  - Measurable precision improvement on curated set  
  - Critical findings include reconfirmation evidence; ingestion steady under moderate load  
  - Findings with CVEs surface better “why this matters” context in the triage and report views

### Phase 4 (Weeks 13–16 | ~60 hours) — Disclosure Helpers + Pro Report + Verified Events + Pilot

- Disclosure helpers  
  - Detect `security.txt`; surface contact hints during “Convert to Issue”

- Professional remediation report  
  - One-off export: formula-safe CSV + PDF with findings, severity, affected URLs, remediation notes, and **CVE metadata (where present)**

- **Verified events for downstream systems**  
  - When a NetGuardian finding is confirmed and converted to Issue (or resolved), emit a verified event carrying:  
    - `cve_id`, `cve_score`, rule id, severity, repo/org, timestamps  
  - Document how BLT-Rewards (Idea B) and RepoTrust (Idea X) can consume these events

- Pilot & release  
  - Pilot with 1–2 orgs; polish; docs (user/admin/setup/contrib); tag v1.0

- Acceptance  
  - Pilot orgs export report and complete disclosure flow using security.txt hints  
  - v1.0 sign-off with working encrypted scanning → CVE-aware triage → issue conversion → verified events

## Benefits

- Credible scanning foundation: real detections + verifiable evidence (not demo output).
- Privacy-preserving by default: sensitive evidence stays encrypted end-to-end; decrypt happens client-side for authorized users.
- Lower reviewer workload: normalized findings, dedup, CVE filters, and triage-lite handoff reduce time spent sorting noise.
- **CVE-aware context out of the box:** NetGuardian reuses BLT’s CVE cache/search so findings carry `cve_id` + `cve_score` and link cleanly into BLT’s CVE explorer.
- Better disclosure hygiene: security.txt hints streamline responsible outreach.
- Practical outputs for orgs: professional CSV/PDF remediation reports with CVE metadata support remediation tracking.
- Trusted signals for other ideas: verified events with CVE metadata feed BLT-Rewards (Idea B) and RepoTrust (Idea X) without duplicating detection work.
