# Project H — BLT Growth: Sizzle-First Contributor Progress & AI-Guided Issue Recommendation

## Overview

**One line:** Time-aware contributor growth system that uses Sizzle (time tracking) to drive personal progress, AI-guided "what to work on next," and maintainer capacity visibility.

**Project Type:** Single 350-hour GSoC project

**Primary Goal:** Answer "where am I in my journey?" and "what should I work on next, and why?" for each contributor using time-aware progress tracking and AI-guided recommendations.

---

## Problem Statement

Current challenges in BLT:

1. **Progress = PR count:** Contributors measure progress by number of PRs, not quality or alignment with BLT's core mission (bug logging).
2. **No growth direction:** Contributors don't know what to work on next to grow their skills or contribute meaningfully.
3. **Maintainer overload:** Maintainers struggle to match issues to contributors who have relevant experience or capacity.
4. **Slop and gaming:** Low-quality PRs pushed to "rank up" without meaningful contribution to BLT's core goals.
5. **Time data underutilized:** Sizzle (time tracking) exists but isn't used to drive growth, recommendations, or capacity planning.

---

## Solution: BLT Growth

A **Sizzle-first contributor growth system** with **two delivery modes**:

### Delivery Mode 1: Dashboard-Based Recommendations (Pull)
Contributors visit the **Growth Dashboard** to see:
- Their progress journey and skill focus
- AI-recommended next issues with reasoning
- Sizzle time breakdown and maintainer capacity view

### Delivery Mode 2: PR Merged Guidance (Push) — Proactive Mentoring
When a contributor's PR is merged, the AI **proactively** sends guidance:
- "Congrats! Here's what you learned from this contribution"
- "Your growth profile has been updated: XSS (3 fixes) → SQLi (1 fix)"
- "Here's your next challenge: Issue #58 (auth context) — estimated ~8h"

This gives contributors **one mentor-style moment** without requiring full event-driven infrastructure.

---

### Core Features

#### 1. Progress Tracker
Shows where contributors **actually spent time** (Sizzle), not just PR count:
- **Journey view:** Timeline of PRs with skill focus (e.g., XSS → SQLi → auth progression)
- **Skill focus inference:** From Sizzle `focus_tag` (when set) or Issue labels (fallback)
- **Meaningful contribution signal:** Alignment with BLT core (bug/security/logging) vs slop
- **Progress = quality + alignment + time**, not volume

#### 2. AI-Guided Issue Recommendation
Suggests **concrete next issues** for each contributor:
- **Why this issue:** Fit to their level, impact on BLT, alignment with core mission
- **What you'll learn:** e.g., "parameterized queries," "auth context," "Django forms"
- **Estimated time:** ~8h from Sizzle patterns of similar contributors
- Uses: Sizzle data + contribution history + goal alignment + Gemini free tier (or local LLM)

#### 3. Sustainable Pace & Re-engagement
- **Sustainable pace:** "Similar contributors who did 10h/week often burned out; 5h/week sustained"
- **Re-engagement nudges:** "No Sizzle for 3 weeks — here are 2 small issues to ease back in"
- **Goal alignment:** "You said you want auth focus; 70% of your Sizzle is auth — aligned"

#### 4. Maintainer Value
- **Capacity visibility:** "This month: 40h on XSS, 20h on SQLi, 5h on auth — we're under-invested in auth"
- **Smart issue–contributor matching:** "Who has deep Sizzle + quality work in area X? Assign #47 to them"
- **Time-to-merge insights:** "Contributors who log time early merge 30% faster"

#### 5. PR Merged Guidance (Proactive Mentoring)
When a PR is merged:
- **Webhook detects:** `pull_request.closed` + `merged=true`
- **Celery task triggers:** Analyze contribution, update GrowthProfile
- **AI generates:** Summary of what was learned + next challenge suggestion
- **Notification delivered:** In-app notification (BLT's existing Notification model)

---

## Technical Approach

### Architecture
- **Built into BLT repo:** Django/DRF infrastructure (TimeLog, Issue, UserProfile models)
- **New models:** ContributorGrowthProfile, ContributionAnalysis, IssueRecommendation
- **New services:** GrowthTrackerService, IssueRecommenderService, SizzleIntegratorService
- **APIs:** RESTful endpoints for growth profile, analyses, recommended issues, time breakdown
- **Frontend:** Growth dashboard, contribution history, Sizzle time charts (Django templates + optional React/Vue)
- **Async infrastructure:** Celery + Redis for background LLM calls (required for PR merged guidance)
- **Webhook extension:** Extend existing `github_webhook()` to handle PR merged events

### Sizzle Extensions (Minimal, Backward-Compatible)
Add two optional fields to `TimeLog` model:
1. **`focus_tag`** (CharField, optional): User selects skill focus at timer start/stop (e.g., "XSS", "SQLi", "Auth", "Docs", "Other")
   - Makes "time per skill" **first-class** instead of inferred
2. **`github_pr_url`** (URLField, optional): Associate time with PRs as well as issues
   - Enables "time-to-merge," "time per PR" metrics

**Effort:** ~33h / 350h (~9% of scope)

### AI Integration
- **LLM:** Gemini free tier (or local model like Ollama) for:
  - Recommendation reasoning ("why this issue")
  - Alignment scoring (BLT core vs out-of-scope)
  - Skill inference (from contribution history)
- **Prompts:** "Given contributor's Sizzle (25h XSS, 10h SQLi) + past PRs, recommend next issue from open BLT issues with reasoning"
- **No paid API required:** Gemini free tier or self-hosted

### Data Flow

**Dashboard Flow (Pull):**
1. **Contributor works on issue** → logs time in Sizzle (with optional `focus_tag`)
2. **Contributor visits dashboard** → requests recommendations
3. **AI generates recommendations** → top N issues with "why" + "what you'll learn" + time estimate
4. **Dashboard shows:** progress, recommended issues, Sizzle time breakdown, maintainer capacity view

**PR Merged Flow (Push):**
1. **Contributor's PR is merged** → GitHub webhook fires
2. **Webhook handler detects** `pull_request.closed` + `merged=true`
3. **Celery task queued** → runs asynchronously (avoids webhook timeout)
4. **Task analyzes contribution** → creates ContributionAnalysis (quality, alignment, skills)
5. **Growth profile updated** → skill areas, meaningful contribution count, growth phase
6. **AI generates guidance** → summary of what was learned + next challenge suggestion
7. **Notification delivered** → in-app notification via BLT's Notification model

---

## Deliverables (350h Scope)

### Phase 1: Sizzle Alignment (~33h)
- Add `focus_tag` and `github_pr_url` to TimeLog model
- Migration, serializer, API, UI (dropdown for focus, PR URL field)
- Tests and docs

### Phase 2: Async Infrastructure (~25h)
- Set up Celery with Redis as message broker
- Configure `blt/celery.py` and worker process
- Task decorators, error handling, retry logic
- Integration with existing Django settings

### Phase 3: Data Models & Services (~70h)
- ContributorGrowthProfile, ContributionAnalysis, IssueRecommendation models
- GrowthTrackerService (analyze contributions, infer skills)
- IssueRecommenderService (generate recommendations, score issues)
- SizzleIntegratorService (time per skill, focus timeline, enrich recommendations)

### Phase 4: AI/LLM Integration (~50h)
- Gemini free tier setup (or Ollama)
- Prompts for recommendation reasoning, alignment scoring, skill inference
- Prompts for PR merged guidance (what you learned, next challenge)
- Error handling, rate limiting, caching

### Phase 5: PR Merged Guidance (~40h)
- Extend `github_webhook()` to handle `pull_request.closed` + `merged=true`
- Celery task to analyze merged PR and update GrowthProfile
- AI call to generate "what you learned" + "next challenge" guidance
- Deliver via BLT's Notification model (in-app notification)

### Phase 6: APIs (~35h)
- GrowthProfileViewSet, ContributionAnalysisViewSet, RecommendedIssuesViewSet
- Serializers, permissions, filtering
- Time breakdown API

### Phase 7: Frontend (~60h)
- Growth dashboard (progress, scores, recommended issues)
- Contribution history page
- Sizzle time charts (time per skill, focus over time)
- Notification display for PR merged guidance
- Responsive design, UI polish

### Phase 8: Testing & Documentation (~37h)
- Unit tests (services, models, Celery tasks)
- API tests
- Webhook integration tests (mock GitHub events)
- User docs, API docs, developer guide

**Total: 350h**

---

## Differentiation from Other Projects

| Aspect | Project B (Rewards) | Project F (Quality Leaderboards) | **Project H (BLT Growth)** |
|--------|---------------------|----------------------------------|----------------------------|
| **Focus** | Rewards (BACON, badges) | Ranking by quality | Personal growth + direction |
| **Question** | "What did you earn?" | "Who's best?" | "What's my progress? What's next?" |
| **Output** | Leaderboard, BACON | Quality-first leaderboard | Progress dashboard, AI recommendations |
| **Time/Sizzle** | Not used | Optional signal | **Core lens** (time = progress) |
| **AI** | Optional | Optional | **Core** (recommendations, reasoning) |
| **Audience** | Active contributors | Community (comparison) | **Individual** (self-improvement) |

**Key differentiator:** BLT Growth is **Sizzle-first** — time tracking drives progress, recommendations, and maintainer value. No other project uses time as the main lens.

---

## Success Metrics

### For Contributors
- % of contributors who view their growth dashboard weekly
- % of contributors who accept AI-recommended issues
- Average "meaningful contribution" score improvement over 3 months
- Re-engagement rate (contributors who return after gaps)

### For Maintainers
- Time saved on issue assignment (measured by "time to first contributor claim")
- % of issues matched to contributors with relevant Sizzle history
- Reduction in out-of-scope PRs (measured by "alignment score" trend)

### For Community
- % of community time spent on BLT core (bug/security/logging) vs other
- Time-to-merge for PRs from contributors who log Sizzle
- Contributor retention (% still active after 6 months)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **Low Sizzle adoption** | PR merged guidance shows value even without Sizzle; nudges encourage logging; `focus_tag` is optional |
| **AI recommendation quality** | Start with rule-based + templates; add Gemini incrementally; human-in-loop (contributor can dismiss) |
| **Celery complexity** | Use Django-Q as fallback (simpler); document setup clearly; mentor support for infrastructure |
| **Webhook reliability** | Implement retry logic; graceful degradation (dashboard still works if webhook fails); logging and monitoring |
| **LLM latency/cost** | Celery handles async; Gemini free tier is sufficient; cache common patterns; fall back to templates if LLM fails |
| **Scope creep** | Clear boundary: only PR merged event in scope; issue claimed and PR opened are Phase 2 |
| **Overlap with B or F** | Clear positioning: B = rewards, F = ranking, H = growth + direction; H can feed B but doesn't implement BACON |

---

## Future Extensions (Out of 350h Scope)

The following are **Phase 2** features that build on the foundation established in this project:

- **Full event-driven mentoring:** AI guidance on issue claimed, PR opened (not just PR merged)
- **GitHub comment delivery:** Post AI guidance as GitHub PR comments (in addition to in-app notifications)
- **Auto-create TimeLogs:** GitHub webhooks that automatically start/stop Sizzle timers on issue assignment / PR open
- **Burnout detection:** Analyze Sizzle patterns to detect unsustainable pace and suggest breaks
- **Mentorship matching:** Pair experienced contributors with learners based on skill areas
- **Learning paths:** Structured sequences of issues for skill progression (e.g., "XSS track: 5 issues, ~40h")
- **Slack/Discord integration:** Deliver AI guidance via Slack or Discord bots
- **Codebase-aware recommendations:** Use RAG to index BLT codebase and provide code-level guidance ("start in `auth.py:45`")

---

## Why This Project Matters

1. **Addresses real pain:** Maintainer burden, AI slop, lack of growth direction — all confirmed by BLT contributors
2. **Unique angle:** No other OSS project uses time tracking (Sizzle) as the main lens for contributor growth
3. **Proactive mentoring:** PR merged guidance gives contributors a **mentor-style experience** — AI reaches out when they accomplish something, not just when they ask
4. **AI + Security + Education:** Blends AI (recommendations), security (BLT core alignment), and education (what you'll learn) — aligns with GSoC 2026 themes
5. **Immediate value:** Dashboard + PR merged guidance delivers value from day one
6. **Foundation for full mentoring:** Celery infrastructure enables future expansion to issue claimed, PR opened, and other events
7. **Scalable:** RESTful APIs mean external tools (e.g., IDE extensions, Slack bots) can consume growth data

---

## Getting Started (For GSoC Contributors)

### Prerequisites
- Familiarity with Django, Django REST Framework
- Basic understanding of LLMs (Gemini API or Ollama)
- Experience with GitHub API and webhooks
- Basic knowledge of Celery or async task queues
- Optional: React/Vue for frontend (or Django templates)

### Mentorship Needs
- **BLT maintainer:** Guidance on BLT core goals, Sizzle usage patterns, contributor pain points
- **AI/ML mentor:** Help with Gemini prompts, recommendation quality, alignment scoring
- **UX mentor:** Dashboard design, contributor-facing UI, maintainer capacity view

### Community Bonding Period
- Study Sizzle (TimeLog model, existing UI)
- Study existing webhook infrastructure (`website/views/user.py:github_webhook()`)
- Set up local Celery + Redis environment
- Interview 5–10 BLT contributors: "What would help you grow?"
- Draft initial prompts for Gemini (recommendation reasoning + PR merged guidance)
- Wireframe growth dashboard and notification UI

---

## Infrastructure References (from codebase analysis)

| Component | Location | Notes |
|-----------|----------|-------|
| **GitHub webhook handler** | `website/views/user.py:github_webhook()` | Extend to handle `pull_request.closed` + `merged=true` |
| **Notification model** | `website/models.py` (line ~2390) | Use for in-app delivery of PR merged guidance |
| **GitHub comment pattern** | `website/views/bounty.py` (line ~380-390) | Reference for GitHub API integration |
| **Signal pattern** | `website/social_signals.py` | Follow for event-driven architecture |
| **Sizzle (TimeLog)** | `website/models.py`, `website/views/organization.py` | Extend with `focus_tag`, `github_pr_url` |

**New files to create:**
- `blt/celery.py` — Celery app configuration
- `website/tasks.py` — Celery tasks for LLM calls and notification delivery
- `website/services/growth_tracker.py` — GrowthTrackerService
- `website/services/issue_recommender.py` — IssueRecommenderService

---

## References

- **BLT repo:** https://github.com/OWASP-BLT/BLT
- **Discussion #5495:** Community direction (2025-2026)
- **Sizzle (TimeLog):** `website/models.py` (TimeLog model), `website/views/organization.py` (TimeLogListView)
- **Gemini free tier:** https://ai.google.dev/pricing
- **Celery docs:** https://docs.celeryq.dev/
- **Similar concept (PR readiness):** [Good To Go](https://dsifry.github.io/goodtogo/) (inspiration for time-bounded, goal-aligned recommendations)

---

## Contact

For questions about this project idea:
- **Maintainer:** [Tag maintainer in OWASP-BLT/BLT-GSoC-Ideas discussions]
- **Contributor (draft author):** @Pritz395

---

**Last updated:** January 2026
