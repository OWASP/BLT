# Project Ideas — Brief Overview

A short reference of BLT GSoC project options. 

---

## Purpose

Synthesizes community direction (Discussion #5495). Each standalone project fits one 350-hour slot. 

---

### Project A — CVE Detection & Validation Pipeline

[View full details →](Project-A.md)

**One line:** Opt-in pipeline from scanner/GitHub → NVD validation → GHSC model and verification UI/API.

---

### Project B — Security Contribution Gamification & Recognition

[View full details →](Project-B.md)

**One line:** Consume verified security contributions to award BACON/badges, reputation tiers, leaderboards, and challenges.

---

### Project C — blt-education Platform (standalone)

**One line:** Tiered learning tracks, hands-on labs, auto-quizzes, and instructor review workflows.

[View full details →](Project-C.md)

---

### Project D — Knowledge Sharing & Community Impact (standalone)

**One line:** Anonymized aggregation, public dashboards, reports, and remediation playbooks.

[View full details →](Project-D.md)

---

### Project E — PR Readiness Tracker & Contributor Dashboard

**One line:** Web-based PR readiness checker with CI aggregation, discussion analysis, reviewer intent detection, and a contributor-facing dashboard.

[View full details →](Project-E.md)

---

## Differentiation (standalone options)

| Project | Focus | Beneficiaries | Dependencies | Risk level |
|---------|--------|---------------|--------------|------------|
| A | Detection + validation | Maintainers, contributors | NVD, scanning | High (false positives) |
| B | Rewards + recognition | Active contributors | Verified signals (or mocks) | Medium (gaming, economics) |
| C | Education platform | New contributors | Content, mentoring | Medium (content burden) |
| D | Knowledge sharing | OSS ecosystem | Aggregated data, governance | Medium (privacy) |
| E | PR readiness & workflow | Contributors, maintainers | GitHub API, (optional) BLT auth | Medium (API limits, parsers) |

---

## Decision guide

Choose by primary goal (one project per slot):

- **Rewards & recognition for verified security work** (BACON, badges, leaderboards, education bridge) → **Project B + light C**
- **CVE detection & verification pipeline** (GHSC, NVD, maintainer verification UI/API) → **Project A**
- **PR readiness & merge workflow** (CI aggregation, discussion analysis, reviewer intent, web dashboard) → **Project E**
- **Structured education & knowledge sharing** (labs, playbooks, dashboards, approval workflow) → **Project C + D** (combined into one 350h project)

---

## Cross-cutting notes

- **Decoupling B from A:** B is designed around a generic “verified security contribution” event; it does not require Project A. Fixtures or a small admin UI can supply events during GSoC; A→B integration is optional later.
- **A + B in one 350-hour slot:** Not recommended; both need focused scope, testing, and pilot time. Treat as two separate projects.
- **C + D combined:** One 350-hour project is possible: education platform (tracks, labs, quizzes, review) plus knowledge-sharing (anonymization, dashboards, playbooks, approval workflow). Shares data and governance concerns.
- **Project E and A:** E (PR readiness) is independent. Optionally, “PR ready” from E could later feed into A’s pipeline (e.g. only consider PRs for GHSC once readiness is READY or after manual triage), but that integration is out of scope for a single 350h slot.

---
