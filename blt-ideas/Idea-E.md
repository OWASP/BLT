# Idea E — PR Readiness & Security Dashboard (350h)

## Overview
A **350-hour development effort** focused on giving contributors and maintainers a clear, actionable view of **PR readiness, CI/CD health, and security status**.  
The idea extends the original 175h scope by deepening security analysis, improving triage workflows, and scaling the dashboard for real-world maintainer usage.

The goal is to reduce review friction, surface real risks early, and help maintainers make faster, safer merge decisions.

---

## Goals
- Aggregate CI/CD results from GitHub Actions and other check-runs.
- Analyze PR discussions to classify **actionable vs non-actionable comments**.
- Detect reviewer intent (**blocking**, **needs changes**, **suggestion**, **nitpick**).
- Provide expanded **security signal visibility** per PR:
  - SAST results
  - Secret scanning status
  - Dependency and configuration issues
  - Security bot findings
- Introduce **security-aware PR readiness states**:
  - READY
  - ACTION_REQUIRED
  - BLOCKED (security or CI)
- Provide maintainers with a **single dashboard** to track:
  - Risky PRs
  - Unresolved discussions
  - Security warnings
  - Review bottlenecks

---

## Security & Bug Focus
- Highlight PRs with **failing or risky security checks**.
- Correlate security findings with PR changes instead of showing raw tool output.
- Reduce false positives by prioritizing findings that affect changed code paths.
- Surface **clear remediation hints** (links, docs, guidance — not auto-fixes).
- Optional integration with BLT Security Bot outputs for deeper triage.

---

## Dashboard Capabilities
- PR readiness summary at a glance.
- CI/CD pass/fail indicators.
- Security warnings grouped by severity.
- Reviewer comment breakdown:
  - Blocking
  - Needs changes
  - Suggestions
  - Resolved
- Maintainer-focused queues:
  - High-risk PRs
  - PRs blocked on security
  - PRs waiting on contributor action

---

## Mockup
![PR Readiness & Security Dashboard](https://github.com/user-attachments/assets/192ff514-3539-427f-8224-176ae60c18fd)

> Note: This mockup is illustrative and will evolve with maintainer feedback.

---

## Week-by-Week Timeline (350h)

### Community Bonding (Weeks 1–2)
- Understand BLT workflows, repositories, and maintainer expectations
- Finalize scope, success metrics, and dashboard requirements
- Review existing CI, security tools, and PR processes
- Setup development environment and access

---

### Phase 1 — Core Foundations

**Week 3**
- PR metadata ingestion
- CI/CD check-run aggregation
- Initial PR readiness state logic

**Week 4**
- Basic dashboard UI
- READY / ACTION_REQUIRED / BLOCKED states
- CI failure handling and visual indicators

---

### Phase 2 — Review & Discussion Intelligence

**Week 5**
- PR comment ingestion and threading
- Actionable vs non-actionable comment classification

**Week 6**
- Reviewer intent detection (blocking, suggestion, nitpick)
- Resolved vs unresolved discussion tracking

---

### Phase 3 — Security Signal Integration

**Week 7**
- Security tool result ingestion (SAST, secrets, dependency checks)
- Normalize security findings per PR

**Week 8**
- Correlate security findings with changed files and lines
- Severity vs impact prioritization logic

**Week 9**
- Security-aware blocking rules
- False-positive reduction based on PR context

---

### Phase 4 — Maintainer Triage & Scaling

**Week 10**
- Maintainer queues (high-risk PRs, blocked PRs)
- Filtering and sorting by risk and status

**Week 11**
- Audit trail for PR readiness changes
- Historical view of PR security and review status

**Week 12**
- Performance optimization for larger repositories
- Caching and pagination improvements

---

### Phase 5 — Polish & Handover

**Week 13**
- UX improvements based on maintainer feedback
- Documentation for contributors and maintainers

**Week 14**
- End-to-end testing on real BLT repositories
- Bug fixes and stability improvements

**Week 15**
- Final refinements
- Deployment and maintenance documentation

**Week 16**
- Final evaluation
- Demo to mentors and maintainers
- Knowledge transfer and future roadmap discussion

---

## Benefits
- Contributors clearly see **what blocks their PR**.
- Maintainers quickly identify **risky or stalled PRs**.
- Reduced manual review overhead.
- Earlier detection of security and configuration issues.
- Scalable foundation for future BLT security tooling.

---

## Future Enhancements (Post-development)
- AI-assisted security remediation triage
- SOC-style security dashboards
- Reviewer recommendation improvements
- Integration with BLT engagement and reward systems

---

*Last Updated: January 2026*
