# BLT Ideas — Brief Overview

A short reference of BLT brainstorming ideas for potential future development.

---

## Purpose

Synthesizes community direction (Discussion #5495). Each standalone idea fits one 350-hour development slot. These are currently brainstorming ideas and not official project commitments yet.

---

### Idea A — CVE Detection & Validation Pipeline

[View full details →](Idea-A.md)

**One line:** Opt-in pipeline from scanner/GitHub → NVD validation → GHSC model and verification UI/API.

---

### Idea B — Security Contribution Gamification & Recognition

[View full details →](Idea-B.md)

**One line:** Consume verified security contributions to award BACON/badges, reputation tiers, leaderboards, and challenges.

**Description:** Listens for verified GHSC (or equivalent) events and awards rewards idempotently: BACON, badges, reputation tiers (Beginner → Trusted), severity-weighted leaderboards, and security challenges. Includes admin audit and basic fraud controls. Does not do detection or NVD; assumes a feed of verified contributions (real or mocked).

**Add-on (optional): light C (education bridge)**  
Idea B can be extended with a **light C** add-on in the same 350-hour slot. Light C is _not_ a separate idea: it adds read-only APIs and an optional webhook that expose badge/reputation and leaderboard data (no raw CVE or vulnerability details). Future education platforms can use these to unlock courses or show contributor standing. No labs, no curriculum — just the APIs so B's outputs can drive education tooling. The **recommended** approach is **B + light C** as one idea.

---

### Idea C — blt-education Platform (standalone)

[View full details →](Idea-C.md)

**One line:** Tiered learning tracks, hands-on labs, auto-quizzes, and instructor review workflows.

---

### Idea D — Knowledge Sharing & Community Impact (standalone)

[View full details →](Idea-D.md)

**One line:** Anonymized aggregation, public dashboards, reports, and remediation playbooks.

---

### Idea E — PR Readiness Tracker & Contributor Dashboard 

[View full details →](Idea-E.md)

**One line:** Web-based PR readiness checker with CI aggregation, discussion analysis, reviewer intent detection, and a contributor-facing dashboard.

**Description:** A single 350-hour effort that answers "when is this PR actually ready?" in one place. **CI aggregation** combines all GitHub check runs and commit statuses into one pass/fail/pending state. **Discussion analysis** classifies review comments (e.g. actionable vs non-actionable vs resolved) and tracks thread resolution so contributors know what still needs a response. **Reviewer intent detection** distinguishes blocking feedback from suggestions and nitpicks (with support for common bots like CodeRabbit, Cursor, etc.). Contributors drop PRs into a **web dashboard** to track readiness across multiple PRs, re-check after addressing feedback, and get a clear status (e.g. READY, ACTION_REQUIRED, CI_FAILING). Can integrate with BLT's GitHub workflows and optionally feed into verification pipelines (e.g. Idea A) later. Inspired by the [Good To Go](https://dsifry.github.io/goodtogo/) approach (deterministic PR readiness) but adds a BLT-hosted web UI and deeper discussion/reviewer-intent analysis.

---

### Idea E (Extended) — AI-Assisted Security Remediation Triage Platform

[View full details →](Idea-E(Extended).md)

**One line:** Advisory security triage for PRs with explainable insights on security-relevant changes and remediation guidance.

**Description:** Extends Idea E with a security-focused triage layer that analyzes PR diffs, CI results, and review context to identify potential security hardening issues (e.g., unsafe TLS configuration, token handling, CI/CD injection risks). Findings are _advisory only_ and exposed as GitHub check annotations/comments and a BLT-hosted web view. No exploit storage, no automated blocking, and no CVE detection.

**Scope-notes:**

- Deterministic rules first; optional ML assistance for prioritization
- Human-in-the-loop review to reduce false positives
- Builds directly on Idea E's CI aggregation and discussion analysis
- Optional future integration with Idea A is out of scope

---

### Idea F — Contributor Security Reputation Graph (Quality-First Leaderboards)

[View full details →](Idea-F.md)

**One line:** Quality-driven contributor reputation and leaderboard system that ranks trust and impact instead of raw activity.

**Description:** Implements a security-first reputation graph that aggregates verified security contributions across BLT (PR fixes, reviews, remediation outcomes) and computes contributor trust scores. The system emphasizes signal quality over volume, weighting factors like fix correctness, severity impact, review usefulness, and false-positive rates. Provides maintainers with confidence signals for triage and delegation, and exposes read-only APIs for downstream systems (rewards, dashboards, education). Designed with opt-in visibility, auditability, and strong anti-gaming controls.

---

### Idea G — NetGuardian: Distributed Autonomous Security Scanning & Validation Platform

[View full details →](Idea-G.md)

**One line:** Community-powered security scanning platform with distributed scanning, real vulnerability detection, and responsible disclosure workflows.

**Description:** Replaces stubbed scanners with real vulnerability detection, introduces distributed scanning via secure volunteer clients, adds result validation and false-positive filtering, enables autonomous discovery (CT logs, GitHub, blockchain), and improves disclosure workflows. Focuses on accuracy, validation, and responsible disclosure to help identify real-world vulnerabilities.

---

### Idea H — BLT Growth: Sizzle-First Contributor Progress & AI-Guided Issue Recommendation

[View full details →](Idea-H.md)

**One line:** Time-aware contributor growth system that uses Sizzle (time tracking) to drive personal progress, AI-guided "what to work on next," and proactive mentoring on PR merge.

**Description:** A single 350-hour effort that answers "where am I in my journey?" and "what should I work on next, and why?" for each contributor. Two delivery modes: (1) **Dashboard-based recommendations** where contributors pull AI-guided suggestions, and (2) **PR merged guidance** where the AI proactively reaches out when a PR is merged with "here's what you learned" + "here's your next challenge." **Progress tracker** shows where contributors actually spent time (Sizzle), skill focus inferred from Sizzle `focus_tag` (when set) and Issue labels (fallback) — e.g., XSS → SQLi → auth progression — and a **meaningful contribution** signal (alignment with BLT core vs slop). **AI-guided issue recommendation** suggests concrete next issues with **why this issue**, **what you'll learn**, and **estimated time** (~8h from Sizzle patterns). Gives **maintainers** capacity visibility and smart issue–contributor matching. Includes **Celery async infrastructure** for reliable LLM calls and **webhook extension** for PR merged events. AI uses Gemini free tier (or local model). Distinct from Idea B (rewards) and Idea F (leaderboards); H = personal growth + direction.

**Scope notes:**
- Sizzle alignment: Add optional `focus_tag` and `github_pr_url` to TimeLog
- Async infrastructure: Celery + Redis for background LLM calls
- Progress tracker: Journey view, skill focus, meaningful vs slop signal
- AI recommendations: Gemini free tier; "why this issue" + "what you'll learn"
- PR merged guidance: Webhook extension + Celery task + AI guidance + notification delivery
- Dashboard & APIs: Web UI, REST endpoints, testing, docs

---

### Idea I — First-Time Contributor Experience & AI-Assisted Security Guide

[View full details →](Idea-I.md)

**One line:** Security-first onboarding, documentation clarity, and an AI-assisted guide to help contributors understand BLT and OWASP expectations before contributing.

**Description:** Improves BLT's first-time contributor experience by addressing onboarding, navigation, and documentation gaps that lead to insecure or low-quality contributions. The effort introduces a clear "start here" walkthrough for new users, security-focused information architecture, and contribution clarity pages that explain what qualifies as a security contribution and why PRs may be rejected. Includes a constrained, explain-only AI Security Guide embedded into the website that answers contributor questions in beginner-friendly language using BLT documentation, GitHub Discussions, and OWASP public resources (e.g. OWASP Top 10, Cheat Sheet Series). The AI does not review code, analyze diffs, approve PRs, or generate exploit guidance; it is strictly scoped to explanation, clarification, and linking to authoritative sources.

---

### Idea J — BLT Cybersecurity News API with Vulnerability Intelligence Dashboard

[View full details →](Idea-J.md)

**One line:** Cybersecurity intelligence platform that transforms public CVEs, advisories, and security news into a personalized vulnerability intelligence dashboard, API, and newsletter.

**Description:** Builds a BLT cybersecurity intelligence platform that transforms public CVEs, advisories, and security news into a personalized vulnerability intelligence dashboard, API, and newsletter for OWASP BLT users. Each vulnerability is presented as part of a broader security intelligence view—linking CVEs, advisories, and reported incidents to affected technology stacks, risk categories, and observed attack patterns. The platform helps users quickly understand what happened, who was impacted, and why it matters, without performing vulnerability detection, validation, or disclosure workflows.

---
### Idea N — RAG AI Bot for Intelligent Onboarding & Security Learning

[View full details →](Idea-N.md)

**One line:** Replace the inoperative chatbot with a RAG-powered AI assistant for user/contributor onboarding, CVE result clarification, security education without disclosing vulnerabilities and other features.

---

### Idea L — Automated Bounty & Reward Pipeline System

[View full details →](Idea-L.md)

**One line:** Complete automated pipeline for bug bounties and rewards with GitHub integration, social media automation, and native payment processing.

**Description:** Comprehensive dual-system approach combining automated vulnerability reporting with bacon rewards and a native bounty management system. Features GitHub integration via `/bounty - $X` commands, automated issue listing on website, contributor registration system, maintainer verification workflows, and `/reward` command for automated payouts. Includes bacon reward distribution for verified organizations, automated X (Twitter) posting for community presence, and native payment gateway integration. Creates two complementary systems: vulnerability reporting with bacon incentivization, and bounty management kinda like an open source Opire/Algora for faster adoption and community growth.

---

### Idea M — CVE Remediation Pipeline (sits on top of discovery from Idea A and/or Idea G (NetGuardian))

[View full details →](Idea-M.md)

**One line:** Full remediation lifecycle from discovery to AI-verified fix: consumes findings from discovery (performed by Idea A and/or Idea G (NetGuardian), or both) via webhooks, tracks merged fixes, verifies root cause is addressed and identifies related patterns, and emits verified remediation events to B.

**Description:** A 350-hour effort with a **different purpose** from Idea A. Discovery in the ideas list can be performed by **either Idea A or Idea G (NetGuardian), or both** — A and G overlap on discovery. Idea M does **remediation** only: it consumes findings from whichever discovery source(s) exist (A and/or G) via webhooks and manages the full lifecycle from discovered → merged → AI verified. Core value: fix quality (AI verification that root cause is addressed, similar patterns elsewhere), remediation dashboard, and verified events to Idea B. Does not conflict with Idea E (E = pre-merge readiness: CI, discussion, reviewer intent; M = post-merge: did the fix truly resolve the CVE, related patterns, ready to count for B).

---

### Idea K — Core BLT Frontend Migration to Next.js/TypeScript

[View full details →](Idea-K.md)

**One line:** Migrate BLT frontend from Django templates to Next.js/TypeScript on Cloudflare Pages for edge-optimized, zero-latency global access.

---

### Idea O — BLT-Smart-Reporter AI Explainer

[View full details →](Idea-O.md)

**One line:** Modernize the OWASP BLT browser extension with restored functionality and AI-assisted vulnerability reporting.

---

### Idea P — Secure API Development & Migration to Django Ninja

[View full details →](Idea-P.md)

**One line:** Deliver a secure, fast v2 API on Django Ninja alongside existing DRF v1, then deprecate v1 with OpenAPI-first SDKs.

---

### Idea Q — Toasty: AI Triage & Responsible Disclosure Assistant

[View full details →](Idea-Q.md)

**One line:** AI-powered triage and responsible disclosure assistant for vulnerability management.

---

### Idea R — BLT Flutter App Modernization & Mobile Contributor Companion

[View full details →](Idea-R.md)

**One line:** Modernize the BLT Flutter mobile app as a contributor companion tool.

---

### Idea S — BLT-CVE Explorer & Resilient Multi-Source CVE Mirror

[View full details →](Idea-S.md)

**One line:** Build a resilient CVE data explorer with multi-source mirroring capabilities.

---

### Idea T — BLT Target Registry

[View full details →](Idea-T.md)

**One line:** Passive directory of security-friendly projects for vulnerability research.

---

### Idea U — Pre-Contribution Security Intent & Risk Guidance

[View full details →](Idea-U.md)

**One line:** Provide security intent and risk guidance before contributors submit code.

---

### Idea V — Unified Event-Driven Gamification Engine

[View full details →](Idea-V.md)

**One line:** Event-driven gamification engine for unified rewards and recognition across BLT.

---

### Idea W — BLT Security Campaigns

[View full details →](Idea-W.md)

**One line:** Time-bound, maintainer-friendly security campaigns with curated issues and progress tracking.

---

### Idea X — RepoTrust Score

[View full details →](Idea-X.md)

**One line:** A single, explainable 0-100 security-health score for OSS repos.

---

### Idea Y — SecureCall: Privacy-First Video Call Note Taker for Bug Disclosure Discussions

[View full details →](Idea-Y.md)

**One line:** A secure video call note taker that doesn't save transcriptions and can be useful when talking securely about bug disclosures.

---

### Idea Z — BLT-MCP: Model Context Protocol Server for Complete BLT Interface

[View full details →](Idea-Z.md)

**One line:** A Model Context Protocol (MCP) server that provides comprehensive, AI-agent-friendly access to all aspects of BLT including issues, repos, contributions, rewards, and workflows.

---

## 2026 Grouped Idea List

### Large Projects (Consolidated)

| Group | Description | Ideas |
| --- | --- | --- |
| CVE Detection Pipeline | End-to-end vulnerability pipeline: scanning, CVE validation, and remediation lifecycle | [A](Idea-A.md), [G](Idea-G.md), [M](Idea-M.md) |
| Security Education Platform | Hands-on security labs, contributor onboarding UX, AI guidance (RAG chatbot), and pre-PR advisory workflows | [C](Idea-C.md), [D](Idea-D.md), [I](Idea-I.md), [N](Idea-N.md), [L2](Idea-L2.md) |
| Gamification & Contributor Growth | BACON rewards, bounty pipeline, reputation scoring, contributor growth powered by an event engine | [B](Idea-B.md), [L](Idea-L.md), [F](Idea-F.md), [V](Idea-V.md), [H](Idea-H.md) |
| AI Review Intelligence | AI-driven issue triage, PR security analysis, and mining of historical review patterns | [E.1](Idea-E.1.md), [Q](Idea-Q.md), [M-S](Idea-M-S.md) |
| Platform Core Architecture | BLT frontend migration, API v1 | [K](Idea-K.md), [P](Idea-P.md) |
| MCP | AI agent-first interface and CLI | [Z](Idea-Z.md) |

### Medium Projects (Standalone)

| Idea | Description |
| --- | --- |
| [J](Idea-J.md) | Aggregates CVEs and advisories into searchable dashboards and newsletters |
| [O](Idea-O.md) | Cross-browser extension with AI explanations for vulnerabilities |
| [R](Idea-R.md) | Mobile bug reporting, offline drafts, and contributor dashboards |
| [T](Idea-T.md) | Directory of projects that welcome responsible disclosure |
| [W](Idea-W.md) | Time-boxed security improvement campaigns with curated issues |
| [X](Idea-X.md) | Explainable trust score for repositories using public signals |
| [Y](Idea-Y.md) | Ephemeral secure video call tool for disclosure discussions with zero persistence |

### Small Projects

| Idea | Description |
| --- | --- |
| [RS](Idea-RS.md) | Flags low-effort or duplicate vulnerability reports before review |
| [S](Idea-S.md) | Community notes, watchlists, export tools, and audit logging |

---

## Cross-cutting notes

- **A and G overlap on discovery:** Idea A (CVE Detection & Validation Pipeline) and Idea G (NetGuardian) both perform discovery (A = scanner/GitHub → NVD → GHSC; G = distributed scanning). They can overlap; discovery in the ideas list can be performed by either A or G or both. Idea M (CVE Remediation Pipeline) consumes findings from whichever discovery source(s) exist.
- **Decoupling B from A:** B is designed around a generic "verified security contribution" event; it does not require Idea A. Fixtures or a small admin UI can supply events during development; A→B integration is optional later.
- **A + B in one 350-hour slot:** Not recommended; both need focused scope, testing, and pilot time. Treat as two separate ideas.
- **C + D combined:** One 350-hour effort is possible: education platform (tracks, labs, quizzes, review) plus knowledge-sharing (anonymization, dashboards, playbooks, approval workflow). Shares data and governance concerns.
- **Idea E and A:** E (PR readiness) is independent. Optionally, "PR ready" from E could later feed into A's pipeline (e.g. only consider PRs for GHSC once readiness is READY or after manual triage), but that integration is out of scope for a single 350h slot.
- **Idea E (Extended) and E:** E (Extended) builds directly on Idea E's CI aggregation and discussion analysis, adding security-focused triage. Can be done as a standalone idea or as an extension.
- **Idea H and B:** H (BLT Growth) focuses on personal growth and AI-guided recommendations; B focuses on rewards and leaderboards. H can optionally feed a "meaningful contribution" or alignment score to B for reward weighting, but H does not implement BACON or leaderboards itself. They are complementary: B = "you earned X"; H = "here's your growth path and what to do next."
- **Idea F as foundation for B:** F (trust & reputation) provides the scoring engine that B (rewards) can leverage. However, F is designed as a standalone system with read-only APIs. B can operate independently with simple contribution counts during development; F→B integration is a natural evolution but not required.
- **F and A synergy:** A (detection & validation) produces verified fix events that F uses to build reputation scores. F's trust scores can help A prioritize which contributors' submissions to fast-track. Both benefit from shared data but can run independently.
- **Standalone F scope:** Idea F focuses on the scoring engine, data model, anti-gaming controls, and API layer. UI/dashboards for displaying scores are minimal (admin-only); consumer-facing displays would be built by Ideas B, C, or D as integrations.
- **Idea G independence:** G (NetGuardian) is a standalone security scanning platform. It can optionally feed findings to Idea A for validation, but operates independently with its own scanning infrastructure and volunteer network.
- **Idea I impact:** I (first-time contributor experience) improves onboarding across all ideas by establishing clear documentation, navigation, and expectations. Benefits all other ideas by reducing low-quality or insecure contributions.
- **Idea J as intelligence layer:** J (vulnerability intelligence) aggregates public security data for awareness and visibility. Does not perform detection or validation like Idea A, but can complement it by providing context on disclosed vulnerabilities.
- **Idea L automation scope:** L (automated bounty & reward pipeline) focuses on workflow automation and payment processing. Integrates with existing BLT bot infrastructure and can complement Idea B's reward system by providing the bounty management layer. Social media automation increases community visibility across all ideas.
- **Idea Y for disclosure security:** Y (SecureCall) provides privacy-first video call note-taking specifically for sensitive bug disclosure discussions. Natural fit for Idea A (CVE Detection) workflows and Idea M (Remediation Pipeline) where maintainers and researchers need to discuss vulnerabilities without retention risk. Ephemeral architecture ensures no long-term storage of exploit details.
- **Idea Z as integration layer:** Z (BLT-MCP) provides standardized, AI-agent-friendly access to all BLT features. Complements multiple ideas by exposing their capabilities through MCP protocol: Idea B (rewards/badges), Idea F (reputation scores), Idea H (AI recommendations), Idea N (RAG bot). Positions BLT as MCP-native platform for AI agents like Claude Desktop.

---

## Hours Analysis

### 🎯 Ideas Well-Scoped to 350 Hours

| Idea | Hours | Status | Notes |
|------|-------|--------|-------|
| **C** - Education Platform | 320-330 | ✅ Well-scoped | Content creation is less AI-acceleratable |
| **E** - PR Readiness Dashboard | 350 | ✅ Well-scoped | Good timeline breakdown |
| **E-Ext** - Security Triage | 350 | ✅ Well-scoped | Builds on Idea E |
| **G** - NetGuardian | 330 | ✅ Well-scoped | Security domain needs expertise |
| **H** - BLT Growth | 350 | ✅ Well-scoped | Sizzle-first approach is clear |
| **L** - Bounty Pipeline | 350 | ✅ Well-scoped | Payment systems need careful implementation |

### ⚡ May Be Faster with AI (250-320 hours)

| Idea | Estimated with AI | Status | Recommendation |
|------|------------------|--------|----------------|
| **K** - Frontend Migration | 250-280 | ⚠️ Fast with AI | Add stretch goals or deeper testing |
| **J** - News API | 280-320 | ⚠️ Fast with AI | Consider adding advanced features |

### ⚠️ Need Scope Clarification

| Idea | Issue | Recommendation |
|------|-------|----------------|
| **A** - CVE Pipeline | No timeline | Add detailed phase breakdown |
| **B** - Gamification | Unclear if includes "light C" | Clarify scope, may be 400+ hours with light C |
| **D** - Knowledge Sharing | Too short (200-250h) | Combine with Idea C or expand scope |

### 🔴 May Need Scope Reduction

| Idea | Estimated Hours | Status | Recommendation |
|------|----------------|--------|----------------|
| **F** - Reputation Graph | 400-500 | ⚠️ Too ambitious | Focus on core engine, defer standalone app |
| **I** - Onboarding | 400-450 | ⚠️ Too ambitious | Simplify AI guide, focus on key pages |

### AI Acceleration Impact

**🚀 High Impact (50-70% faster)**
- UI/Dashboard development
- API endpoint creation
- TypeScript/component migration
- Data pipeline setup

**Ideas:** K, J, E, H, L

**⚙️ Medium Impact (30-50% faster)**
- Infrastructure code
- Integration logic
- Basic CRUD operations

**Ideas:** C, E-Ext, I

**🎓 Low Impact (10-30% faster)**
- Security algorithm design
- Educational content creation
- Anti-gaming logic
- Domain-specific validation

**Ideas:** A, B, F, G

### Key Takeaway

> While AI coding significantly accelerates UI/API-heavy ideas (K, J, E, H, L), it has limited impact on those requiring **security expertise and domain knowledge** (A, F, G). Ideas C, E, G, H, and L are **best calibrated** for 350 hours considering AI assistance.

---

## Interested Contributors

We would like to acknowledge the following interested contributors who have expressed interest in contributing to BLT:

- **DonnieBLT** - Maintainer and mentor

_This section will be updated as contributors express interest in these ideas._

---

_Last Updated: February 2026_
