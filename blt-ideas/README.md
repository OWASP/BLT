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
Project B can be extended with a **light C** add-on in the same 350-hour slot. Light C is _not_ a separate project: it adds read-only APIs and an optional webhook that expose badge/reputation and leaderboard data (no raw CVE or vulnerability details). Future education platforms can use these to unlock courses or show contributor standing. No labs, no curriculum — just the APIs so B's outputs can drive education tooling. The **recommended** proposal is **B + light C** as one project.

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

**Description:** A single 350-hour project that answers "when is this PR actually ready?" in one place. **CI aggregation** combines all GitHub check runs and commit statuses into one pass/fail/pending state. **Discussion analysis** classifies review comments (e.g. actionable vs non-actionable vs resolved) and tracks thread resolution so contributors know what still needs a response. **Reviewer intent detection** distinguishes blocking feedback from suggestions and nitpicks (with support for common bots like CodeRabbit, Cursor, etc.). Contributors drop PRs into a **web dashboard** to track readiness across multiple PRs, re-check after addressing feedback, and get a clear status (e.g. READY, ACTION_REQUIRED, CI_FAILING). Aligns with GSoC goals around contributor tooling and AI-assisted workflows; can integrate with BLT's GitHub workflows and optionally feed into verification pipelines (e.g. Project A) later. Inspired by the [Good To Go](https://dsifry.github.io/goodtogo/) approach (deterministic PR readiness) but adds a BLT-hosted web UI and deeper discussion/reviewer-intent analysis.

#### Project E (Extension) — AI-Assisted Security Remediation Triage

**One line:**  
Advisory security triage for PRs that flags risky patterns and surfaces explainable remediation guidance via GitHub and a BLT dashboard.

**Description:**
Extends Project E with a security-focused triage layer that analyzes PR diffs, CI results, and review context to identify potential security hardening issues (e.g., unsafe TLS configuration, token handling, CI/CD injection risks). Findings are _advisory only_ and exposed as GitHub check annotations/comments and a BLT-hosted web view. No exploit storage, no automated blocking, and no CVE detection.

**Scope-notes:**

- Deterministic rules first; optional ML assistance for prioritization
- Human-in-the-loop review to reduce false positives
- Builds directly on Project E's CI aggregation and discussion analysis
- Optional future integration with Project A is out of scope

---

### Project H — BLT Growth: Sizzle-First Contributor Progress & AI-Guided Issue Recommendation

**One line:** Time-aware contributor growth system that uses Sizzle (time tracking) to drive personal progress, AI-guided "what to work on next," and proactive mentoring on PR merge.

**Description:** A single 350-hour project that answers "where am I in my journey?" and "what should I work on next, and why?" for each contributor. Two delivery modes: (1) **Dashboard-based recommendations** where contributors pull AI-guided suggestions, and (2) **PR merged guidance** where the AI proactively reaches out when a PR is merged with "here's what you learned" + "here's your next challenge." **Progress tracker** shows where contributors actually spent time (Sizzle), skill focus inferred from Sizzle `focus_tag` (when set) and Issue labels (fallback) — e.g., XSS → SQLi → auth progression — and a **meaningful contribution** signal (alignment with BLT core vs slop). **AI-guided issue recommendation** suggests concrete next issues with **why this issue**, **what you'll learn**, and **estimated time** (~8h from Sizzle patterns). Gives **maintainers** capacity visibility and smart issue–contributor matching. Includes **Celery async infrastructure** for reliable LLM calls and **webhook extension** for PR merged events. AI uses Gemini free tier (or local model). Distinct from Project B (rewards) and Project F (leaderboards); H = personal growth + direction.

**Scope notes:**

- Sizzle alignment (~33h): Add optional `focus_tag` and `github_pr_url` to TimeLog.
- Async infrastructure (~25h): Celery + Redis for background LLM calls.
- Progress tracker (~70h): Journey view, skill focus, meaningful vs slop signal.
- AI recommendations (~50h): Gemini free tier; "why this issue" + "what you'll learn."
- PR merged guidance (~40h): Webhook extension + Celery task + AI guidance + notification delivery.
- Dashboard & APIs (~95h): Web UI, REST endpoints, testing, docs.

---

### Project M — CVE Remediation Pipeline (sits on top of discovery from Project A and/or Project G (NetGuardian))

[View full details →](Project-M.md)

**One line:** Full remediation lifecycle from discovery to AI-verified fix: consumes findings from discovery (performed by Project A and/or Project G (NetGuardian), or both) via webhooks, tracks merged fixes, verifies root cause is addressed and identifies related patterns, and emits verified remediation events to B.

**Description:** A 350-hour project with a **different purpose** from Project A. Discovery in the ideas list can be performed by **either Project A or Project G (NetGuardian), or both** — A and G overlap on discovery. Project M does **remediation** only: it consumes findings from whichever discovery source(s) exist (A and/or G) via webhooks and manages the full lifecycle from discovered → merged → AI verified. Core value: fix quality (AI verification that root cause is addressed, similar patterns elsewhere), remediation dashboard, and verified events to Project B. Does not conflict with Project E (E = pre-merge readiness: CI, discussion, reviewer intent; M = post-merge: did the fix truly resolve the CVE, related patterns, ready to count for B).

---

## Differentiation (standalone options)

| Project | Focus                                                     | Beneficiaries                        | Dependencies                                                        | Risk level                            |
| ------- | --------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------- | ------------------------------------- |
| A       | Detection + validation                                    | Maintainers, contributors            | NVD, scanning                                                       | High (false positives)                |
| B       | Rewards + recognition                                     | Active contributors                  | Verified signals (or mocks)                                         | Medium (gaming, economics)            |
| C       | Education platform                                        | New contributors                     | Content, mentoring                                                  | Medium (content burden)               |
| D       | Knowledge sharing                                         | OSS ecosystem                        | Aggregated data, governance                                         | Medium (privacy)                      |
| E       | PR readiness & workflow                                   | Contributors, maintainers            | GitHub API, (optional) BLT auth                                     | Medium (API limits, parsers)          |
| H       | Contributor growth + time-aware recommendations           | Individual contributors, maintainers | Sizzle (time tracking), Gemini free tier (or local LLM), GitHub API | Medium (Sizzle adoption, LLM quality) |
| M       | Remediation lifecycle (discovered → merged → AI verified) | Maintainers, contributors            | Discovery (A and/or G) webhooks, Gemini free tier (or local LLM)    | Medium (AI verification quality)      |

---

## Decision guide

Choose by primary goal (one project per slot):

- **Rewards & recognition for verified security work** (BACON, badges, leaderboards, education bridge) → **Project B + light C**
- **CVE detection & verification pipeline** (GHSC, NVD, maintainer verification UI/API) → **Project A**
- **PR readiness & merge workflow** (CI aggregation, discussion analysis, reviewer intent, web dashboard) → **Project E**
- **Structured education & knowledge sharing** (labs, playbooks, dashboards, approval workflow) → **Project C + D** (combined into one 350h project)
- **Contributor growth, time-aware progress, and AI-guided "what to work on next"** (Sizzle-first, personal dashboard, maintainer capacity) → **Project H (BLT Growth)**
- **CVE remediation lifecycle on top of discovery (A and/or G)** (discovered → merged → AI verified, fix quality, remediation dashboard, events to B) → **Project M (CVE Remediation Pipeline)**

---

## Cross-cutting notes

- **A and G overlap on discovery:** Project A (CVE Detection & Validation Pipeline) and Project G (NetGuardian) both perform discovery (A = scanner/GitHub → NVD → GHSC; G = distributed scanning). They can overlap; discovery in the ideas list can be performed by either A or G or both. Project M (CVE Remediation Pipeline) consumes findings from whichever discovery source(s) exist.
- **Decoupling B from A:** B is designed around a generic "verified security contribution" event; it does not require Project A. Fixtures or a small admin UI can supply events during GSoC; A→B integration is optional later.
- **A + B in one 350-hour slot:** Not recommended; both need focused scope, testing, and pilot time. Treat as two separate projects.
- **C + D combined:** One 350-hour project is possible: education platform (tracks, labs, quizzes, review) plus knowledge-sharing (anonymization, dashboards, playbooks, approval workflow). Shares data and governance concerns.
- **Project E and A:** E (PR readiness) is independent. Optionally, "PR ready" from E could later feed into A's pipeline (e.g. only consider PRs for GHSC once readiness is READY or after manual triage), but that integration is out of scope for a single 350h slot.
- **Project H and B:** H (BLT Growth) focuses on personal growth and AI-guided recommendations; B focuses on rewards and leaderboards. H can optionally feed a "meaningful contribution" or alignment score to B for reward weighting, but H does not implement BACON or leaderboards itself. They are complementary: B = "you earned X"; H = "here's your growth path and what to do next."
- **Project M and discovery (A and/or G):** Discovery can be performed by **Project A and/or Project G (NetGuardian), or both** — A and G overlap on discovery. M consumes findings from whichever source(s) exist via webhooks and manages the remediation lifecycle (discovered → merged → AI verified), then emits verified remediation events to B. M has a different purpose from A (A = discovery/validation; M = remediation).
- **Project M and E:** E is pre-merge (CI, discussion, reviewer intent); M is post-merge (fix correctness, related patterns, ready to count for B). No conflict.
- **Project M and B:** M emits verified remediation events to B; B consumes M's output. M does not implement BACON or leaderboards.

---
