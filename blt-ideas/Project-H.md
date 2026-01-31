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

A **Sizzle-first contributor growth system** that:

### 1. Progress Tracker
Shows where contributors **actually spent time** (Sizzle), not just PR count:
- **Journey view:** Timeline of PRs with skill focus (e.g., XSS → SQLi → auth progression)
- **Skill focus inference:** From Sizzle `focus_tag` (when set) or Issue labels (fallback)
- **Meaningful contribution signal:** Alignment with BLT core (bug/security/logging) vs slop
- **Progress = quality + alignment + time**, not volume

### 2. AI-Guided Issue Recommendation
Suggests **concrete next issues** for each contributor:
- **Why this issue:** Fit to their level, impact on BLT, alignment with core mission
- **What you'll learn:** e.g., "parameterized queries," "auth context," "Django forms"
- **Estimated time:** ~8h from Sizzle patterns of similar contributors
- Uses: Sizzle data + contribution history + goal alignment + Gemini free tier (or local LLM)

### 3. Sustainable Pace & Re-engagement
- **Sustainable pace:** "Similar contributors who did 10h/week often burned out; 5h/week sustained"
- **Re-engagement nudges:** "No Sizzle for 3 weeks — here are 2 small issues to ease back in"
- **Goal alignment:** "You said you want auth focus; 70% of your Sizzle is auth — aligned"

### 4. Maintainer Value
- **Capacity visibility:** "This month: 40h on XSS, 20h on SQLi, 5h on auth — we're under-invested in auth"
- **Smart issue–contributor matching:** "Who has deep Sizzle + quality work in area X? Assign #47 to them"
- **Time-to-merge insights:** "Contributors who log time early merge 30% faster"

---

## Technical Approach

### Architecture
- **Built into BLT repo:** Django/DRF infrastructure (TimeLog, Issue, UserProfile models)
- **New models:** ContributorGrowthProfile, ContributionAnalysis, IssueRecommendation
- **New services:** GrowthTrackerService, IssueRecommenderService, SizzleIntegratorService
- **APIs:** RESTful endpoints for growth profile, analyses, recommended issues, time breakdown
- **Frontend:** Growth dashboard, contribution history, Sizzle time charts (Django templates + optional React/Vue)

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
1. **Contributor works on issue** → logs time in Sizzle (with optional `focus_tag`)
2. **PR merged** → ContributionAnalysis created (quality score, alignment score, skills demonstrated)
3. **Growth profile updated** → skill areas, meaningful contribution count, growth phase
4. **AI generates recommendations** → top N issues with "why" + "what you'll learn" + time estimate
5. **Dashboard shows:** progress, recommended issues, Sizzle time breakdown, maintainer capacity view

---

## Deliverables (350h Scope)

### Phase 1: Sizzle Alignment (~33h)
- Add `focus_tag` and `github_pr_url` to TimeLog model
- Migration, serializer, API, UI (dropdown for focus, PR URL field)
- Tests and docs

### Phase 2: Data Models & Services (~110h)
- ContributorGrowthProfile, ContributionAnalysis, IssueRecommendation models
- GrowthTrackerService (analyze contributions, infer skills)
- IssueRecommenderService (generate recommendations, score issues)
- SizzleIntegratorService (time per skill, focus timeline, enrich recommendations)

### Phase 3: AI/LLM Integration (~40h)
- Gemini free tier setup (or Ollama)
- Prompts for recommendation reasoning, alignment scoring, skill inference
- Error handling, rate limiting, caching

### Phase 4: APIs (~45h)
- GrowthProfileViewSet, ContributionAnalysisViewSet, RecommendedIssuesViewSet
- Serializers, permissions, filtering
- Time breakdown API

### Phase 5: Frontend (~80h)
- Growth dashboard (progress, scores, recommended issues)
- Contribution history page
- Sizzle time charts (time per skill, focus over time)
- Responsive design, UI polish

### Phase 6: GitHub Integration (~30h)
- Polling for PR data (or webhook as stretch)
- GitHub API calls for PR/issue metadata

### Phase 7: Testing & Documentation (~42h)
- Unit tests (services, models)
- API tests
- Integration tests
- User docs, API docs, developer guide

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
| **Low Sizzle adoption** | Nudges on PR open/merge; show value (recommendations improve with Sizzle data); make `focus_tag` optional |
| **AI recommendation quality** | Start with rule-based + templates; add Gemini incrementally; human-in-loop (contributor can dismiss) |
| **Scope creep** | Clear MVP (33h Sizzle + 317h Growth); defer webhooks, burnout detection, advanced ML to Phase 2 |
| **Overlap with B or F** | Clear positioning: B = rewards, F = ranking, H = growth + direction; H can feed B but doesn't implement BACON |

---

## Future Extensions (Out of 350h Scope)

- **GitHub webhooks** that auto-create/update TimeLogs (40–60h)
- **Automatic timer start/stop** on issue assignment / PR open
- **Burnout detection** from Sizzle patterns (requires consistent logging)
- **Mentorship matching** (pair experienced + learning contributors)
- **Learning paths** (structured sequences of issues for skill progression)

---

## Why This Project Matters

1. **Addresses real pain:** Maintainer burden, AI slop, lack of growth direction — all confirmed by BLT contributors
2. **Unique angle:** No other OSS project uses time tracking (Sizzle) as the main lens for contributor growth
3. **AI + Security + Education:** Blends AI (recommendations), security (BLT core alignment), and education (what you'll learn) — aligns with GSoC 2026 themes
4. **Immediate value:** Even MVP (progress tracker + basic recommendations) delivers value to contributors and maintainers
5. **Scalable:** RESTful APIs mean external tools (e.g., IDE extensions, Slack bots) can consume growth data

---

## Getting Started (For GSoC Contributors)

### Prerequisites
- Familiarity with Django, Django REST Framework
- Basic understanding of LLMs (Gemini API or Ollama)
- Experience with GitHub API
- Optional: React/Vue for frontend (or Django templates)

### Mentorship Needs
- **BLT maintainer:** Guidance on BLT core goals, Sizzle usage patterns, contributor pain points
- **AI/ML mentor:** Help with Gemini prompts, recommendation quality, alignment scoring
- **UX mentor:** Dashboard design, contributor-facing UI, maintainer capacity view

### Community Bonding Period
- Study Sizzle (TimeLog model, existing UI)
- Interview 5–10 BLT contributors: "What would help you grow?"
- Draft initial prompts for Gemini (recommendation reasoning)
- Wireframe growth dashboard and recommendation UI

---

## References

- **BLT repo:** https://github.com/OWASP-BLT/BLT
- **Discussion #5495:** Community direction (2025-2026)
- **Sizzle (TimeLog):** `website/models.py` (TimeLog model), `website/views/organization.py` (TimeLogListView)
- **Gemini free tier:** https://ai.google.dev/pricing
- **Similar concept (PR readiness):** [Good To Go](https://dsifry.github.io/goodtogo/) (inspiration for time-bounded, goal-aligned recommendations)

---

## Contact

For questions about this project idea:
- **Maintainer:** [Tag maintainer in OWASP-BLT/BLT-GSoC-Ideas discussions]
- **Contributor (draft author):** @Pritz395

---

**Last updated:** January 2026
