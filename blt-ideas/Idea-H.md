# Idea H — BLT Growth: Sizzle-First Contributor Progress & AI-Guided Issue Recommendation

## Overview

**One line:** Time-aware contributor growth system that uses Sizzle (time tracking) to drive personal progress, AI-guided "what to work on next," and maintainer capacity visibility.

**Idea Type:** Single 350-hour development effort

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

A **Sizzle-first contributor growth system** with **two delivery modes**.

**Why Sizzle-first?** Time tracking reveals actual investment in learning and contribution quality — a 2-hour typo fix vs. a 20-hour security feature both count as "1 PR," but Sizzle captures the meaningful difference.

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

## Differentiation from Other Projects

| Aspect | Idea B (Rewards) | Idea F (Quality Leaderboards) | **Idea H (BLT Growth)** |
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

## Why This Idea Matters

1. **Addresses real pain:** Maintainer burden, AI slop, lack of growth direction — all confirmed by BLT contributors
2. **Unique angle:** No other OSS project uses time tracking (Sizzle) as the main lens for contributor growth
3. **Proactive mentoring:** PR merged guidance gives contributors a **mentor-style experience** — AI reaches out when they accomplish something, not just when they ask
4. **AI + Security + Education:** Blends AI (recommendations), security (BLT core alignment), and education (what you'll learn) — aligns with 2026 themes
5. **Immediate value:** Dashboard + PR merged guidance delivers value from day one
6. **Foundation for full mentoring:** Celery infrastructure enables future expansion to issue claimed, PR opened, and other events
7. **Scalable:** RESTful APIs mean external tools (e.g., IDE extensions, Slack bots) can consume growth data

---
