# BLT-Vanish Web — Project Roadmap (GSoC 2026)

## Overview

---

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
  - Add Worker `contracts.ts` type guards and contract tests (TS/Dart)
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
