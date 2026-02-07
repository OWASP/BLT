# Project L — Pre-Contribution Security Intent & Risk Guidance (350h)

**Organization:** OWASP Bug Logging Tool (BLT)  
**Program:** Google Summer of Code (development program)  
**Project Type:** Single 350-hour project

---

## 1. Problem Statement

BLT contributors frequently submit pull requests that:
- Touch security-sensitive areas without realizing the associated risk
- Miss basic security expectations or project-specific norms
- Get rejected due to misunderstanding rather than poor intent
- Are created with AI assistance but without adequate security context

Most existing BLT tooling operates **after a pull request already exists**.  
At that point:
- Maintainers repeatedly explain the same security expectations
- Review cycles become longer and more frustrating
- Contributors learn only after rejection

Currently, BLT has **no mechanism that helps contributors understand security risk and expectations before they start coding**.

---

## 2. Project Goal

The goal of this project is to build a **pre-contribution advisory system** that:
- Helps contributors understand security expectations *before opening a PR*
- Gives maintainers early visibility into potentially risky upcoming work
- Reduces insecure or misaligned contributions
- Improves contributor learning without blocking participation

This project focuses on **prevention and clarity**, not enforcement.

---

## 3. Scope Definition

### 3.1 In Scope
- Rule-based evaluation of security context
- Optional contributor intent capture
- Non-blocking, advisory security guidance
- Maintainer visibility into upcoming risky work

### 3.2 Explicitly Out of Scope
- Vulnerability scanning or detection
- CVE creation, validation, or disclosure
- Automated PR approval or rejection
- Code review or diff analysis
- Reputation systems, badges, or scoring
- Any form of enforcement or blocking workflow

---

## 4. High-Level System Overview

The system operates **before PR creation** and is designed to be advisory only.

### High-Level Flow
1. A contributor selects an issue to work on
2. The contributor optionally declares their intent
3. The system evaluates the security context of the issue and repository
4. Advisory guidance is displayed to the contributor
5. Maintainers can view upcoming work that may be security-sensitive

At no point does the system block or gate contribution.

---

## 5. Detailed Feature Description

---

### 5.1 Security Context Evaluation

**Purpose:**  
Identify whether an issue or planned change is likely to be security-sensitive.

**Context Signals Considered:**
- Issue labels indicating security relevance (e.g. authentication, configuration)
- Repository metadata and historical contribution patterns
- Areas of the codebase historically associated with security reviews
- Past pull request outcomes related to similar issues

**Output Characteristics:**
- A simple risk classification (low, medium, high)
- Clear, human-readable reasons explaining why an issue is considered sensitive
- Fully deterministic and explainable logic

No static analysis or code scanning is performed.

---

### 5.2 Contributor Intent Capture

**Purpose:**  
Allow contributors to communicate expectations and assumptions *before* writing code.

**Key Characteristics:**
- Optional and non-blocking
- Lightweight and low-friction
- Informational rather than evaluative

**Intent Information Includes:**
- The general area the contributor plans to work on
- Components or parts of the system they expect to modify
- Whether AI assistance will be used during implementation

This information helps the system provide more relevant guidance and helps maintainers understand upcoming work.

---

### 5.3 Advisory Security Guidance

**Purpose:**  
Provide contributors with early, contextual security guidance before work begins.

**Guidance Characteristics:**
- Plain-language explanations
- Advisory only (no pass/fail states)
- Based on repository history and security context
- Linked to relevant OWASP or BLT documentation

**Examples of Guidance:**
- Highlighting areas that typically require extra validation
- Pointing out common mistakes seen in similar past contributions
- Suggesting relevant security documentation to review

Guidance is intentionally conservative to avoid noise or warning fatigue.

---

### 5.4 Maintainer Visibility Dashboard

**Purpose:**  
Give maintainers early visibility into upcoming security-sensitive contributions.

**Dashboard Capabilities:**
- View contributors who have declared intent on issues
- See which issues are classified as higher risk
- Understand why an issue is considered sensitive
- Identify recurring patterns of misunderstanding

**Benefits for Maintainers:**
- Earlier clarification before PRs are opened
- Reduced repetitive review feedback
- Better issue assignment and mentoring

The dashboard is informational and does not introduce approval gates.

---

### 5.5 Learning and Feedback Loop (Optional)

After a pull request is merged or rejected:
- Declared intent can be compared with the outcome
- Common misunderstanding patterns can be identified
- Guidance rules can be refined over time

No contributor scoring, penalties, or rankings are introduced.

---

## 6. Technical Approach (Conceptual)

- Built on top of BLT’s existing backend and frontend architecture
- Uses existing issue, label, and pull request metadata
- Exposes simple REST-style endpoints for intent and guidance
- Integrates into existing BLT UI flows (issue pages, maintainer views)

No external scanners, vulnerability feeds, or machine learning models are required.

---

## 7. Timeline and Deliverables (350 Hours)

### Community Bonding (Weeks 1–2)
- Study BLT contribution and review workflows
- Align on security context rules with maintainers
- Finalize scope and guardrails

---

### Phase 1 — Security Context Evaluation (Weeks 3–5 | ~90h)
- Define and implement rule-based security context logic
- Validate rules against historical BLT data
- Document decision logic

---

### Phase 2 — Contributor Intent Capture (Weeks 6–7 | ~60h)
- Design and integrate intent capture UI
- Implement backend support and validation
- Ensure privacy and minimal friction

---

### Phase 3 — Advisory Guidance (Weeks 8–10 | ~80h)
- Define guidance templates
- Map security context and intent to guidance
- Reduce false positives and over-warning

---

### Phase 4 — Maintainer Dashboard (Weeks 11–12 | ~70h)
- Build maintainer-facing visibility views
- Add filtering and repository-level summaries
- Collect maintainer feedback

---

### Phase 5 — Testing and Documentation (Weeks 13–16 | ~50h)
- End-to-end testing with real repositories
- Contributor documentation
- Maintainer usage guide
- Deployment and handover notes

---

## 8. Success Metrics

### Contributor-Focused
- Reduction in PR rejections caused by misunderstood security expectations
- Improved contributor confidence before submitting PRs

### Maintainer-Focused
- Reduced repetitive security review comments
- Earlier identification of risky contributions

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|----|----|
| Low adoption of intent capture | Keep flow optional and low-friction |
| Over-warning contributors | Conservative rules and minimal guidance |
| Scope creep | Strict avoidance of scanning and enforcement |
| Privacy concerns | No code or diff storage |

---

## 10. Relationship to Other BLT Projects

- Complements PR Readiness and workflow tooling
- Supports contributor growth and education initiatives
- Does not overlap with CVE detection, scanning, or enforcement projects

---

## 11. Summary

This project introduces a **pre-contribution security awareness layer** for BLT.

By guiding contributors **before code is written**, it:
- Prevents common security mistakes
- Reduces maintainer workload
- Improves contributor understanding
- Aligns with OWASP’s preventive security philosophy
