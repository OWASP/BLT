# Project Ideas — Brief Overview

A short reference of BLT GSoC project options. 

---

## Purpose

Synthesizes community direction (Discussion #5495). Each standalone project fits one 350-hour slot. 

---

### Project A — CVE Detection & Validation Pipeline

**One line:** Opt-in pipeline from scanner/GitHub → NVD validation → GHSC model and verification UI/API.

**Description:** Discovers CVE-related contributions from webhooks and scanner output (e.g. Buttercup), validates against NVD, deduplicates and scores findings, and exposes them via a maintainer verification dashboard and REST API. Post-disclosure only; no raw exploit storage. Foundation for downstream rewards and education.

---

### Project B — Security Contribution Gamification & Recognition

**One line:** Consume verified security contributions to award BACON/badges, reputation tiers, leaderboards, and challenges.

**Description:** Listens for verified GHSC (or equivalent) events and awards rewards idempotently: BACON, badges, reputation tiers (Beginner → Trusted), severity-weighted leaderboards, and security challenges. Includes admin audit and basic fraud controls. Does not do detection or NVD; assumes a feed of verified contributions (real or mocked).

**Add-on (optional): light C (education bridge)**  
Project B can be extended with a **light C** add-on in the same 350-hour slot. Light C is *not* a separate project: it adds read-only APIs and an optional webhook that expose badge/reputation and leaderboard data (no raw CVE or vulnerability details). Future education platforms can use these to unlock courses or show contributor standing. No labs, no curriculum — just the APIs so B’s outputs can drive education tooling. The **recommended** proposal is **B + light C** as one project.

---

### Project C — blt-education Platform (standalone)

**One line:** Tiered learning tracks, hands-on labs, auto-quizzes, and instructor review workflows.

**Description:** Structured security education: Beginner → Intermediate → Trusted tracks, 4–6 labs, auto-grading, instructor review queue, and optional badge-based unlocks. High content and mentoring load; best when education/content capacity exists.

---

### Project D — Knowledge Sharing & Community Impact (standalone)

**One line:** Anonymized aggregation, public dashboards, reports, and remediation playbooks.

**Description:** Pipeline to anonymize and aggregate BLT security data, then publish dashboards, monthly/quarterly reports, and 3–5 remediation playbooks. Includes two-person approval for sensitive content. Depends on having meaningful data to aggregate.

---

### Project E — PR Readiness Tracker & Contributor Dashboard

**One line:** Web-based PR readiness checker with CI aggregation, discussion analysis, reviewer intent detection, and a contributor-facing dashboard.

**Description:** A single 350-hour project that answers “when is this PR actually ready?” in one place. **CI aggregation** combines all GitHub check runs and commit statuses into one pass/fail/pending state. **Discussion analysis** classifies review comments (e.g. actionable vs non-actionable vs resolved) and tracks thread resolution so contributors know what still needs a response. **Reviewer intent detection** distinguishes blocking feedback from suggestions and nitpicks (with support for common bots like CodeRabbit, Cursor, etc.). Contributors drop PRs into a **web dashboard** to track readiness across multiple PRs, re-check after addressing feedback, and get a clear status (e.g. READY, ACTION_REQUIRED, CI_FAILING). Aligns with GSoC goals around contributor tooling and AI-assisted workflows; can integrate with BLT’s GitHub workflows and optionally feed into verification pipelines (e.g. Project A) later. Inspired by the [Good To Go](https://dsifry.github.io/goodtogo/) approach (deterministic PR readiness) but adds a BLT-hosted web UI and deeper discussion/reviewer-intent analysis.

---

### Project F — UI/UX Standardization & Component System

**One line:** Comprehensive UI/UX overhaul with design guidelines, responsive templates, and reusable component library to eliminate recurring UI fixes.

**Description:** Addresses the 25-40 monthly UI fix PRs by establishing a unified design system and component architecture. Creates strict design guidelines, responsive layout standards, and a library of reusable component templates. Includes comprehensive documentation, implementation guidelines, and migration strategy for existing UI elements. Focuses on accessibility compliance, cross-browser compatibility, and mobile responsiveness. Delivers a maintainable foundation that prevents future UI inconsistencies and reduces maintenance overhead.

---

### Project G — Architecture Modernization & Repository Restructuring

**One line:** Systematic dependency cleanup, repository splitting, and infrastructure documentation for improved maintainability and deployment workflows.

**Description:** Comprehensive architectural review and modernization of the BLT website ecosystem. Identifies and removes unnecessary dependencies, splits monolithic components into focused repositories, and documents all systems and workflows. Includes DevOps pipeline optimization, deployment automation, and clear architectural decision records. Creates migration guides, dependency management strategies, and monitoring solutions. Establishes patterns for future development and reduces technical debt through systematic cleanup and documentation.

---

## Differentiation (standalone options)

| Project | Focus | Beneficiaries | Dependencies | Risk level |
|---------|--------|---------------|--------------|------------|
| A | Detection + validation | Maintainers, contributors | NVD, scanning | High (false positives) |
| B | Rewards + recognition | Active contributors | Verified signals (or mocks) | Medium (gaming, economics) |
| C | Education platform | New contributors | Content, mentoring | Medium (content burden) |
| D | Knowledge sharing | OSS ecosystem | Aggregated data, governance | Medium (privacy) |
| E | PR readiness & workflow | Contributors, maintainers | GitHub API, (optional) BLT auth | Medium (API limits, parsers) |
| F | UI/UX standardization | All users, maintainers | Design resources, frontend expertise | Low (implementation complexity) |
| G | Architecture modernization | Maintainers, developers | Infrastructure access, migration planning | Medium (system complexity) |

---

## Decision guide

Choose by primary goal (one project per slot):

- **Rewards & recognition for verified security work** (BACON, badges, leaderboards, education bridge) → **Project B + light C**
- **CVE detection & verification pipeline** (GHSC, NVD, maintainer verification UI/API) → **Project A**
- **PR readiness & merge workflow** (CI aggregation, discussion analysis, reviewer intent, web dashboard) → **Project E**
- **Structured education & knowledge sharing** (labs, playbooks, dashboards, approval workflow) → **Project C + D** (combined into one 350h project)
- **UI/UX consistency & design system** (responsive templates, component library, design guidelines) → **Project F**
- **Infrastructure modernization & cleanup** (dependency removal, repository restructuring, documentation) → **Project G**

---

## Cross-cutting notes

- **Decoupling B from A:** B is designed around a generic “verified security contribution” event; it does not require Project A. Fixtures or a small admin UI can supply events during GSoC; A→B integration is optional later.
- **A + B in one 350-hour slot:** Not recommended; both need focused scope, testing, and pilot time. Treat as two separate projects.
- **C + D combined:** One 350-hour project is possible: education platform (tracks, labs, quizzes, review) plus knowledge-sharing (anonymization, dashboards, playbooks, approval workflow). Shares data and governance concerns.
- **Project E and A:** E (PR readiness) is independent. Optionally, “PR ready” from E could later feed into A’s pipeline (e.g. only consider PRs for GHSC once readiness is READY or after manual triage), but that integration is out of scope for a single 350h slot.

---
