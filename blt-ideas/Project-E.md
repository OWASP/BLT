# Project E — AI-Assisted Security Remediation Triager & PR Readiness Dashboard (Large – 350h)

**Last Updated:** January 2026

---

## Overview
A 350-hour GSoC project to build a **maintainer-first, AI-assisted security remediation triager** tightly integrated with a **PR Readiness & Security Dashboard**.  
The system prioritizes security findings by real risk, explains *why* issues matter, recommends safe remediation steps, and surfaces a clear **ready-to-merge** signal — without auto-merging.

The design is **repository-scoped**, **human-in-the-loop**, and aligned with BLT’s security-first direction.

---

## Why This Matters
Traditional CI/CD pipelines flood maintainers with low-context alerts. This project adds an intelligent layer that:

- Reduces noise via **rule-first detection**
- Uses AI only when rules are ambiguous
- Prioritizes by **risk and exposure**, not raw severity
- Provides **explainable remediation guidance**
- Presents a **single actionable PR readiness view**

---

## Goals
- Ingest and normalize findings from BLT Security Bot and related automations
- Rule-based baseline triage (secrets, Django ORM raw/extra, CSRF, unsafe templates, config)
- AI-assisted classification and explanations for ambiguous cases (advisory only)
- Risk scoring using asset criticality, exposure hints, and history
- Remediation recommendation engine with safety checks and policy awareness
- GitHub Checks integration for line-level annotations and readiness conclusion
- Dashboard queues for maintainers (risk-ordered)
- Maintainer-initiated Website Security Assist scans
- Auditing, rate limits, and abuse-resistant design

---

## Non-Goals (GSoC Scope)
- Internet-wide scanning or autonomous exploitation
- Auto-merge or fully autonomous remediation
- CNA operations
- Multi-tenant enterprise SOC features
- Full BACON economy or labs platform

---

## Mockup
![PR Readiness & Security Dashboard](https://github.com/user-attachments/assets/192ff514-3539-427f-8224-176ae60c18fd)

> Mockup is illustrative; final UI will evolve with mentor feedback.

---

## High-Level Architecture
```mermaid
flowchart LR
  subgraph GH["GitHub"]
    PR["Pull Request"]
  end

  PR -->|"pull_request opened / synchronize"| WH["BLT Webhook"]
  WH --> Q["Task Queue"]
  Q --> AN["PR Security Analyzer"]

  AN --> RB["Rule-based Detectors<br/>(secrets, ORM, CSRF, templates, config)"]
  AN --> LLM["AI Assistant<br/>(only when rules are ambiguous)"]

  subgraph TRIAGER["Remediation Triager"]
    INJ["Finding Ingest & Normalize"]
    RISK["Risk Scoring Engine"]
    REM["Remediation Mapper"]
    XAI["Explainability (reason traces)"]
  end

  RB --> INJ
  LLM --> INJ
  INJ --> RISK --> REM --> XAI

  INJ --> FND[("SecurityFinding Store")]
  RISK --> FND
  REM --> FND
  AN --> RUN[("PRAnalysisRun")]

  FND --> CK["GitHub Checks API<br/>(or PR comment fallback)"]
  CK --> PR

  subgraph WEB["BLT Website"]
    DASH["Security Dashboard & Queues"]
    ASSIST["Website Security Assist<br/>(maintainer-initiated)"]
  end

  FND --> DASH
  RUN --> DASH
  ASSIST --> AN


---

Core Data Models

classDiagram
  class SecurityFinding {
    id: string
    repo: string
    pr_number: int
    head_sha: string
    file_path: string
    start_line: int
    end_line: int
    severity: string
    status: string
    source: string
    type: string
    cwe_id: string
    confidence: float
    summary: string
    remediation: string
    risk_score: float
    risk_factors: string
    explain_trace: string
    fingerprint: string
    first_detected_at: string
    last_seen_at: string
    analysis_run_id: string
  }

  class PRAnalysisRun {
    id: string
    repo: string
    pr_number: int
    head_sha: string
    files_scanned: int
    findings_count: int
    rules_time_ms: int
    ai_time_ms: int
    conclusion: string
    started_at: string
    finished_at: string
  }

  class RepositoryConfig {
    repo: string
    blocking_threshold: string
    require_human_review_medium: bool
    min_confidence_for_flag: float
    enable_ai: bool
    ai_daily_cap: int
    allow_website_assist: bool
    asset_criticality: string
    exposure_hints: string
  }

  class TriageAction {
    id: string
    finding_id: string
    user_id: string
    action: string
    note: string
    created_at: string
  }

  SecurityFinding --> PRAnalysisRun
  TriageAction --> SecurityFinding
  PRAnalysisRun --> RepositoryConfig


---

PR Readiness Logic

flowchart TD
  A[New or Updated PR] --> B{Analysis fresh for head SHA?}
  B -- No --> C[Enqueue analysis] --> P[Checks: pending]
  B -- Yes --> D[Collect open findings]
  D --> E[Filter to changed lines]
  E --> F{Apply repo thresholds}
  F -- Blocking findings --> G[Checks: failure<br/>(merge blocked)]
  F -- No blocking --> H{Human review required?}
  H -- Yes --> I[Checks: neutral<br/>(triage needed)]
  H -- No --> J[Checks: success<br/>(ready to merge)]


---

AI Usage Disclosure (GSoC-Compliant)

Role: Advisory only — classification, explanation, remediation phrasing

Control: Rule-first; AI only if rule confidence < 0.7

Human-in-the-loop: Required for all medium+ and blocking findings

Privacy: Prompts sanitized; no secrets or PII; diffs truncated

Safety: Rate limits, strict templates, caching, audit logs

Fallback: Fully functional rules-only mode

Opt-in: Repositories may disable AI entirely



---

Success Metrics

≥ 75% precision and ≤ 20% false positives

≥ 40% reduction in “needs-more-info” review churn

≥ 60% maintainer acceptance of remediation suggestions

End-to-end analysis ≤ 2 minutes (p95)

AI usage ≤ 100 calls/day with hard caps

At least one BLT repo adopts blocking on high+critical findings



---

Risks & Mitigations

GitHub API limits: Caching, backoff, idempotent jobs

AI outages/cost spikes: Hard caps, rules-only fallback

False positives: Calibration, suppress rules, per-repo policy

Abuse or malformed input: Validation, strict schemas

Sensitive data exposure: Repo-scoped only; no external scanning



---

Week-by-Week Timeline (16 Weeks / ~350h)

Weeks 1–2: Community bonding, requirements, threat model, architecture
Week 3: Ingest & normalization pipeline
Week 4: Rule-based detectors + tests
Week 5: GitHub Checks + readiness evaluator
Week 6: Dashboard queues & triage actions
Week 7: Dataset curation & labeling pipeline
Week 8: AI-assisted classification prototype
Week 9: False-positive reduction & calibration
Week 10: Risk scoring engine (0–100)
Week 11: Remediation mapper v1
Week 12: Explainability & summaries
Week 13: Website Security Assist integration
Week 14: Hardening & abuse resistance
Week 15: Performance, E2E tests, docs
Week 16: Final polish, demo, handover


---

Deliverables

PR Security Analyzer & Remediation Triager

GitHub Checks annotations and readiness status

Security Dashboard with explainability & triage actions

Repository policy configuration

Test suites and evaluation reports

Deployment documentation and final GSoC report



---

Communication & Mentorship

Weekly mentor sync

Bi-weekly demos

Daily async updates in BLT Slack

Small, reviewable PRs throughout



---

Benefits to BLT

Clear, explainable PR security decisions

Reduced review fatigue and noise

Faster, safer merges

Strong foundation for future SOC and automation work


