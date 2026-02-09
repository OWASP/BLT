# Project E — PR Risk Intelligence & Readiness Dashboard (350h)

## Overview
A 350-hour development effort focused on providing maintainers with decision-level intelligence for pull requests by combining readiness status, contextual risk scoring, and review signals.

Instead of acting as a vulnerability detection system, this project focuses on answering:
- Is this PR ready to merge?
- How risky is this change?
- Which PRs need immediate maintainer attention?

The system aggregates CI/CD status, review activity, repository context, and existing security signals to generate a PR Risk Score and actionable readiness insights. The goal is to reduce review fatigue, prioritize high-impact changes, and improve security awareness without blocking development.

## Key Differentiation
This project does not perform vulnerability scanning or create new security findings. Instead, it:
- Consumes existing signals (CI, security tools, repository context)
- Produces risk prioritization and decision intelligence
- Helps maintainers decide where to focus review effort

This makes it complementary to existing or communal security tooling.

## Goals

### PR Readiness Intelligence
- Aggregate CI/CD results from GitHub Actions and check-runs
- Detect readiness states:
  - READY
  - ACTION_REQUIRED
  - BLOCKED (CI or review)
  - HIGH_RISK_REVIEW_REQUIRED

### PR Risk Scoring Engine
Generate a contextual Risk Score (0–100) based on:

- Change Characteristics
  - Size of diff
  - Critical file modifications (auth, config, workflows)
  - Dependency updates
  - Infrastructure or CI changes

- Repository Sensitivity
  - Security-critical directories
  - Secrets/config locations
  - Workflow and deployment files

- Contributor Context
  - First-time contributor
  - Untrusted fork
  - Large or unusual change patterns

- Security Context (Signal Consumption Only)
  - Presence of SAST alerts
  - Secret scanning flags
  - Dependency vulnerabilities
  - (No new scanning performed)

### Review & Discussion Intelligence
- PR comment ingestion and threading
- Actionable vs non-actionable comment classification
- Reviewer intent detection:
  - Blocking
  - Needs changes
  - Suggestion
  - Nitpick
- Resolved vs unresolved discussion tracking

## Dashboard Capabilities

### Maintainer View
- PR Risk Score and category:
  - Low
  - Medium
  - High
  - Critical
- Queues:
  - High-risk PRs
  - Ready to merge
  - Blocked PRs
  - Waiting on contributor

### PR Detail View
- Risk factors explanation:
  - “Modifies authentication logic”
  - “Updates CI workflow permissions”
  - “Includes dependency upgrade with known vulnerabilities”
- CI/CD status summary
- Security signal summary (ingested, not generated)
- Review discussion status

## Security Focus (OWASP Alignment)
This project supports secure development by:
- Prioritizing changes that impact security-sensitive areas
- Highlighting risky workflow or configuration modifications
- Reducing the chance of high-risk changes being overlooked
- Encouraging human-in-the-loop security review

Important:
- No automated enforcement
- No CVE creation
- No exploit generation
- Advisory and prioritization only

## Mockup

![PR Risk & Readiness Dashboard Mockup]<img width="1536" height="1024" alt="file_0000000017c47209a8d98b9659b8ad9d (1)" src="https://github.com/user-attachments/assets/61a3e989-1bc3-43a7-a2ff-887228d69ac4" />


> Illustrative mockup — final UX will evolve based on maintainer feedback.

## Week-by-Week Timeline (350h)

### Community Bonding (Weeks 1–2)
- Understand BLT workflows and repositories
- Identify sensitive paths and risk factors
- Finalize risk model and success metrics
- Environment setup

### Phase 1 — Data Foundations
**Week 3**
- PR metadata ingestion
- Diff analysis (file paths, size, change types)
- CI/CD check aggregation

**Week 4**
- Initial readiness state logic
- Basic dashboard UI

### Phase 2 — Risk Intelligence Core
**Week 5**
- Repository sensitivity mapping
- Critical path detection (auth, config, workflows)

**Week 6**
- Risk scoring algorithm (rule-based)
- Risk factor explanation engine

### Phase 3 — Review Intelligence
**Week 7**
- Comment ingestion and threading
- Actionable vs non-actionable classification

**Week 8**
- Reviewer intent detection
- Unresolved discussion tracking

### Phase 4 — Security Context Integration
**Week 9**
- Ingest existing security tool outputs (SAST, dependency, secrets)
- Risk score enrichment (no scanning)

**Week 10**
- High-risk PR queue
- Filtering and sorting

### Phase 5 — Scaling & Reliability
**Week 11**
- Audit trail for risk/readiness changes
- Historical PR insights

**Week 12**
- Performance optimization
- Caching and pagination

### Phase 6 — Polish & Handover
**Week 13**
- UX improvements
- Documentation

**Week 14**
- Testing on real BLT repositories

**Week 15**
- Deployment documentation
- Final refinements

**Week 16**
- Demo and evaluation
- Knowledge transfer

## Benefits
- Maintainers focus on high-risk changes first
- Contributors understand why their PR needs attention
- Reduced security oversight risk
- Faster merge decisions
- Scalable foundation for DevSecOps intelligence within BLT

## Future Enhancements
- Machine learning–based risk tuning
- Maintainer feedback learning
- Integration with communal PR analysis tools
- SOC-style repository risk analytics

_Last Updated: January 2026_
