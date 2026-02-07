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

**Description:** Listens for verified GHSC (or equivalent) events and awards rewards idempotently: BACON, badges, reputation tiers (Beginner → Trusted), severity-weighted leaderboards, and security challenges. Includes admin audit and basic fraud controls. Does not do detection or NVD; assumes a feed of verified contributions (real or mocked).

**Add-on (optional): light C (education bridge)**  
Project B can be extended with a **light C** add-on in the same 350-hour slot. Light C is *not* a separate project: it adds read-only APIs and an optional webhook that expose badge/reputation and leaderboard data (no raw CVE or vulnerability details). Future education platforms can use these to unlock courses or show contributor standing. No labs, no curriculum — just the APIs so B's outputs can drive education tooling. The **recommended** proposal is **B + light C** as one project.

---

### Project C — blt-education Platform (standalone)

[View full details →](Project-C.md)

**One line:** Tiered learning tracks, hands-on labs, auto-quizzes, and instructor review workflows.

---

### Project D — Knowledge Sharing & Community Impact (standalone)

[View full details →](Project-D.md)

**One line:** Anonymized aggregation, public dashboards, reports, and remediation playbooks.

---

### Project E — PR Readiness Tracker & Contributor Dashboard 

[View full details →](Project-E.md)

**One line:** Web-based PR readiness checker with CI aggregation, discussion analysis, reviewer intent detection, and a contributor-facing dashboard.

**Description:** A single 350-hour project that answers "when is this PR actually ready?" in one place. **CI aggregation** combines all GitHub check runs and commit statuses into one pass/fail/pending state. **Discussion analysis** classifies review comments (e.g. actionable vs non-actionable vs resolved) and tracks thread resolution so contributors know what still needs a response. **Reviewer intent detection** distinguishes blocking feedback from suggestions and nitpicks (with support for common bots like CodeRabbit, Cursor, etc.). Contributors drop PRs into a **web dashboard** to track readiness across multiple PRs, re-check after addressing feedback, and get a clear status (e.g. READY, ACTION_REQUIRED, CI_FAILING). Aligns with GSoC goals around contributor tooling and AI-assisted workflows; can integrate with BLT's GitHub workflows and optionally feed into verification pipelines (e.g. Project A) later. Inspired by the [Good To Go](https://dsifry.github.io/goodtogo/) approach (deterministic PR readiness) but adds a BLT-hosted web UI and deeper discussion/reviewer-intent analysis.

---

### Project E (Extended) — AI-Assisted Security Remediation Triage Platform

[View full details →](Project-E(Extended).md)

**One line:** Advisory security triage for PRs with explainable insights on security-relevant changes and remediation guidance.

**Description:** Extends Project E with a security-focused triage layer that analyzes PR diffs, CI results, and review context to identify potential security hardening issues (e.g., unsafe TLS configuration, token handling, CI/CD injection risks). Findings are _advisory only_ and exposed as GitHub check annotations/comments and a BLT-hosted web view. No exploit storage, no automated blocking, and no CVE detection.

**Scope-notes:**  
- Deterministic rules first; optional ML assistance for prioritization  
- Human-in-the-loop review to reduce false positives  
- Builds directly on Project E's CI aggregation and discussion analysis  
- Optional future integration with Project A is out of scope

---

### Project F — Contributor Security Reputation Graph (Quality-First Leaderboards)

[View full details →](Project-F.md)

**One line:** Quality-driven contributor reputation and leaderboard system that ranks trust and impact instead of raw activity.

**Description:** Implements a security-first reputation graph that aggregates verified security contributions across BLT (PR fixes, reviews, remediation outcomes) and computes contributor trust scores. The system emphasizes signal quality over volume, weighting factors like fix correctness, severity impact, review usefulness, and false-positive rates. Provides maintainers with confidence signals for triage and delegation, and exposes read-only APIs for downstream systems (rewards, dashboards, education). Designed with opt-in visibility, auditability, and strong anti-gaming controls.

---

### Project G — NetGuardian: Distributed Autonomous Security Scanning & Validation Platform

[View full details →](Project-G.md)

**One line:** Community-powered security scanning platform with distributed scanning, real vulnerability detection, and responsible disclosure workflows.

**Description:** Replaces stubbed scanners with real vulnerability detection, introduces distributed scanning via secure volunteer clients, adds result validation and false-positive filtering, enables autonomous discovery (CT logs, GitHub, blockchain), and improves disclosure workflows. Focuses on accuracy, validation, and responsible disclosure to help identify real-world vulnerabilities.

---

### Project H — BLT Growth: Sizzle-First Contributor Progress & AI-Guided Issue Recommendation

[View full details →](Project-H.md)

**One line:** Time-aware contributor growth system that uses Sizzle (time tracking) to drive personal progress, AI-guided "what to work on next," and proactive mentoring on PR merge.

**Description:** A single 350-hour project that answers "where am I in my journey?" and "what should I work on next, and why?" for each contributor. Two delivery modes: (1) **Dashboard-based recommendations** where contributors pull AI-guided suggestions, and (2) **PR merged guidance** where the AI proactively reaches out when a PR is merged with "here's what you learned" + "here's your next challenge." **Progress tracker** shows where contributors actually spent time (Sizzle), skill focus inferred from Sizzle `focus_tag` (when set) and Issue labels (fallback) — e.g., XSS → SQLi → auth progression — and a **meaningful contribution** signal (alignment with BLT core vs slop). **AI-guided issue recommendation** suggests concrete next issues with **why this issue**, **what you'll learn**, and **estimated time** (~8h from Sizzle patterns). Gives **maintainers** capacity visibility and smart issue–contributor matching. Includes **Celery async infrastructure** for reliable LLM calls and **webhook extension** for PR merged events. AI uses Gemini free tier (or local model). Distinct from Project B (rewards) and Project F (leaderboards); H = personal growth + direction.

**Scope notes:**
- Sizzle alignment: Add optional `focus_tag` and `github_pr_url` to TimeLog
- Async infrastructure: Celery + Redis for background LLM calls
- Progress tracker: Journey view, skill focus, meaningful vs slop signal
- AI recommendations: Gemini free tier; "why this issue" + "what you'll learn"
- PR merged guidance: Webhook extension + Celery task + AI guidance + notification delivery
- Dashboard & APIs: Web UI, REST endpoints, testing, docs

---

### Project I — First-Time Contributor Experience & AI-Assisted Security Guide

[View full details →](Project-I.md)

**One line:** Security-first onboarding, documentation clarity, and an AI-assisted guide to help contributors understand BLT and OWASP expectations before contributing.

**Description:** Improves BLT's first-time contributor experience by addressing onboarding, navigation, and documentation gaps that lead to insecure or low-quality contributions. The project introduces a clear "start here" walkthrough for new users, security-focused information architecture, and contribution clarity pages that explain what qualifies as a security contribution and why PRs may be rejected. Includes a constrained, explain-only AI Security Guide embedded into the website that answers contributor questions in beginner-friendly language using BLT documentation, GitHub Discussions, and OWASP public resources (e.g. OWASP Top 10, Cheat Sheet Series). The AI does not review code, analyze diffs, approve PRs, or generate exploit guidance; it is strictly scoped to explanation, clarification, and linking to authoritative sources.

---

### Project J — BLT Cybersecurity News API with Vulnerability Intelligence Dashboard

[View full details →](Project-J.md)

**One line:** Cybersecurity intelligence platform that transforms public CVEs, advisories, and security news into a personalized vulnerability intelligence dashboard, API, and newsletter.

**Description:** Builds a BLT cybersecurity intelligence platform that transforms public CVEs, advisories, and security news into a personalized vulnerability intelligence dashboard, API, and newsletter for OWASP BLT users. Each vulnerability is presented as part of a broader security intelligence view—linking CVEs, advisories, and reported incidents to affected technology stacks, risk categories, and observed attack patterns. The platform helps users quickly understand what happened, who was impacted, and why it matters, without performing vulnerability detection, validation, or disclosure workflows.

---
### Project N — RAG AI Bot for Intelligent Onboarding & Security Learning

[View full details →](Project-N.md)

**One line:** Replace the inoperative chatbot with a RAG-powered AI assistant for user/contributor onboarding, CVE result clarification, security education without disclosing vulnerabilities and other features.

---

### Project L — Automated Bounty & Reward Pipeline System

[View full details →](Project-L.md)

**One line:** Complete automated pipeline for bug bounties and rewards with GitHub integration, social media automation, and native payment processing.

**Description:** Comprehensive dual-system approach combining automated vulnerability reporting with bacon rewards and a native bounty management system. Features GitHub integration via `/bounty - $X` commands, automated issue listing on website, contributor registration system, maintainer verification workflows, and `/reward` command for automated payouts. Includes bacon reward distribution for verified organizations, automated X (Twitter) posting for community presence, and native payment gateway integration. Creates two complementary systems: vulnerability reporting with bacon incentivization, and bounty management kinda like an open source Opire/Algora for faster adoption and community growth.

---

## Differentiation (standalone options)

| Project | Focus | Beneficiaries | Dependencies | Risk level |
|---------|-------|---------------|--------------|------------|
| A | Detection + validation | Maintainers, contributors | NVD, scanning | High (false positives) |
| B | Rewards + recognition | Active contributors | Verified signals (or mocks) | Medium (gaming, economics) |
| C | Education platform | New contributors | Content, mentoring | Medium (content burden) |
| D | Knowledge sharing | OSS ecosystem | Aggregated data, governance | Medium (privacy) |
| E | PR readiness & workflow | Contributors, maintainers | GitHub API, (optional) BLT auth | Medium (API limits, parsers) |
| E (Extended) | Security triage for PRs | Contributors, maintainers | Project E, CI signals | Medium (false positives) |
| F | Trust & reputation scoring | Maintainers, reviewers | Verified contributions, BLT data | Medium (gaming, privacy) |
| G | Security scanning platform | Security researchers, maintainers | Scanning tools, volunteer clients | Medium (accuracy, disclosure) |
| H | Contributor growth + time-aware recommendations | Individual contributors, maintainers | Sizzle (time tracking), Gemini free tier (or local LLM), GitHub API | Medium (Sizzle adoption, LLM quality) |
| I | First-time contributor onboarding | New contributors | BLT documentation, OWASP resources | Low (content organization) |
| J | Vulnerability intelligence | BLT users, security teams | Public CVE feeds, security advisories | Medium (data quality, aggregation) |
| N | AI-assisted onboarding & security learning (RAG) | New users, contributors, maintainers | OWASP public resources, GitHub Discussions (read-only), Public CVE feeds | Low–Medium (hallucinations) |
| L | Automated bounty & reward pipeline | Contributors, maintainers, organizations | GitHub API, payment gateway, social media APIs | Medium (payment processing, automation complexity) |

---

## Decision guide

Choose by primary goal (one project per slot):

- **Rewards & recognition for verified security work** (BACON, badges, leaderboards, education bridge) → **Project B + light C**
- **CVE detection & verification pipeline** (GHSC, NVD, maintainer verification UI/API) → **Project A**
- **PR readiness & merge workflow** (CI aggregation, discussion analysis, reviewer intent, web dashboard) → **Project E**
- **PR security triage** (advisory security insights, remediation guidance, GitHub annotations) → **Project E (Extended)**
- **Structured education & knowledge sharing** (labs, playbooks, dashboards, approval workflow) → **Project C + D** (combined into one 350h project)
- **Contributor growth, time-aware progress, and AI-guided "what to work on next"** (Sizzle-first, personal dashboard, maintainer capacity) → **Project H (BLT Growth)**
- **Trust & reputation scoring for contributors** (verified contribution tracking, explainable trust scores, anti-gaming controls) → **Project F**
- **Distributed security scanning platform** (volunteer clients, real vulnerability detection, responsible disclosure) → **Project G (NetGuardian)**
- **First-time contributor experience** (onboarding, documentation clarity, AI-assisted security guide) → **Project I**
- **Vulnerability intelligence & news** (CVE aggregation, dashboard, API, newsletter) → **Project J**
- **Automated bounty & reward pipeline** (GitHub integration, social automation, native payment processing) → **Project L**

---

## Cross-cutting notes

- **Decoupling B from A:** B is designed around a generic "verified security contribution" event; it does not require Project A. Fixtures or a small admin UI can supply events during GSoC; A→B integration is optional later.
- **A + B in one 350-hour slot:** Not recommended; both need focused scope, testing, and pilot time. Treat as two separate projects.
- **C + D combined:** One 350-hour project is possible: education platform (tracks, labs, quizzes, review) plus knowledge-sharing (anonymization, dashboards, playbooks, approval workflow). Shares data and governance concerns.
- **Project E and A:** E (PR readiness) is independent. Optionally, "PR ready" from E could later feed into A's pipeline (e.g. only consider PRs for GHSC once readiness is READY or after manual triage), but that integration is out of scope for a single 350h slot.
- **Project E (Extended) and E:** E (Extended) builds directly on Project E's CI aggregation and discussion analysis, adding security-focused triage. Can be done as a standalone project or as an extension.
- **Project H and B:** H (BLT Growth) focuses on personal growth and AI-guided recommendations; B focuses on rewards and leaderboards. H can optionally feed a "meaningful contribution" or alignment score to B for reward weighting, but H does not implement BACON or leaderboards itself. They are complementary: B = "you earned X"; H = "here's your growth path and what to do next."
- **Project F as foundation for B:** F (trust & reputation) provides the scoring engine that B (rewards) can leverage. However, F is designed as a standalone system with read-only APIs. B can operate independently with simple contribution counts during GSoC; F→B integration is a natural evolution but not required.
- **F and A synergy:** A (detection & validation) produces verified fix events that F uses to build reputation scores. F's trust scores can help A prioritize which contributors' submissions to fast-track. Both benefit from shared data but can run independently.
- **Standalone F scope:** Project F focuses on the scoring engine, data model, anti-gaming controls, and API layer. UI/dashboards for displaying scores are minimal (admin-only); consumer-facing displays would be built by Projects B, C, or D as integrations.
- **Project G independence:** G (NetGuardian) is a standalone security scanning platform. It can optionally feed findings to Project A for validation, but operates independently with its own scanning infrastructure and volunteer network.
- **Project I impact:** I (first-time contributor experience) improves onboarding across all projects by establishing clear documentation, navigation, and expectations. Benefits all other projects by reducing low-quality or insecure contributions.
- **Project J as intelligence layer:** J (vulnerability intelligence) aggregates public security data for awareness and visibility. Does not perform detection or validation like Project A, but can complement it by providing context on disclosed vulnerabilities.
- **Project L automation scope:** L (automated bounty & reward pipeline) focuses on workflow automation and payment processing. Integrates with existing BLT bot infrastructure and can complement Project B's reward system by providing the bounty management layer. Social media automation increases community visibility across all projects.

---

## Interested Students & Contributors

We would like to acknowledge the following interested students and contributors who have expressed interest in GSoC 2026 with BLT:

- **DonnieBLT** - Project maintainer and mentor

_This section will be updated as students express interest and contribute to project proposals._

---

_Last Updated: February 2026_
