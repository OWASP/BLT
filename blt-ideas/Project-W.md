# Project W — BLT Security Campaigns

## One line

Time‑bound, maintainer‑friendly security campaigns (e.g. “30 days of auth hardening”) with curated issues, light guidance, and visible progress tracking.

---

## Problem & personas

- **Founder Frank (small startup founder)** and  
- **Open Source Oliver (maintainer with limited bandwidth)**  

both struggle with “doing security” in the abstract:

- They have dozens of potential security issues but **no concrete, achievable plan**.
- BLT today is very **feature‑oriented** (issues, rewards, education), but there is **no way to run a focused campaign** like “fix the top 10 XSS issues in February” and see structured progress.

They need:

- Time‑boxed pushes instead of never‑ending backlogs,
- A curated, scoped list of issues,
- A simple way to show “we made progress” at the end.

**BLT Security Campaigns** turns this into a first‑class concept.

---

## Core idea

A **campaigns system** that lets maintainers and founders:

1. Choose a **template** (e.g. “Auth Hardening Sprint”, “CVE Fix Week”, “Secure Defaults Upgrade”).
2. Scope it to specific **repos + labels** (e.g. `auth`, `security`, `xss`).
3. Set a **time window** and **goal** (e.g. “30 days, close 5 issues”).
4. Get a **campaign landing page** for contributors with:
   - Curated issue list,
   - Time remaining,
   - Progress bar.
5. Receive an **auto‑generated recap** at the end that can be pasted into GitHub Discussions, blog posts, or internal reports.

This moves BLT from “here are your bugs” to “let’s fix auth together this month”.

---

## Data model (sketch)

```text
Campaign
  - organization (FK → Organization)
  - title, description
  - template (choice: auth_hardening, cve_fix, secure_defaults, …)
  - status (draft / active / completed / cancelled)
  - start_date, end_date
  - goal_count (target issues to close)
  - repos (M2M → Repo)
  - labels (M2M → Label)
  - created_by (FK → User)
  - created_at

CampaignIssue
  - campaign (FK → Campaign)
  - issue (FK → Issue)
  - added_at
  - resolved_at (null until closed during campaign)

CampaignTemplate
  - key (e.g. "auth_hardening")
  - name
  - description
  - recommended_labels (JSON list)
  - recommended_duration_days
  - success_criteria (Markdown)
```

This keeps campaign state explicit, allows flexible scoping via repos + labels, and tracks which issues participated in a campaign and when they were actually resolved.

---

## UX flows

### Maintainer (Founder Frank / Open Source Oliver)

1. **Browse templates**  
   See options like:
   - “Auth Hardening Sprint (30 days)”  
   - “CVE Fix Week”  
   - “Secure Defaults Upgrade”.
2. **Creation wizard**  
   - Pick org + template,  
   - Choose repos + labels,  
   - Set start/end dates and goal count,  
   - Preview campaign landing page, then launch.
3. **Monitor progress**  
   - Progress bar vs goal,  
   - In‑scope issues and their states,  
   - Contributors participating.
4. **End‑of‑campaign recap**  
   - Auto‑generated Markdown summary,  
   - Optional charts (or chart metadata) for dashboards.

### Contributor

- Sees a **campaign banner** on relevant BLT views.
- Clicks into the **campaign landing page** to see:
  - curated issue list,
  - days remaining,
  - current progress.
- Works on issues; closing issues during the campaign window updates `resolved_at` and the progress bar.

---

## Integration points

- **Security views**:
  - Org‑level “Campaigns” list,
  - Per‑campaign landing page route + templates.
- **Optional Project B tie‑in**:
  - Extra recognition (badges, tagged rewards) for campaign contributions,
  - “Campaign Champion” highlight on leaderboards filtered by campaign.

---

## GSoC scope (350h)

**Must‑have (MVP):**

- Campaign / CampaignIssue / CampaignTemplate models + migrations.
- templates: Auth Hardening, CVE Fix Week, Secure Defaults Upgrade.
- Maintainer creation wizard (simple but solid).
- Contributor‑facing landing page with progress bar.
- Progress tracking wired to real issue state changes.
- Markdown recap generator + basic API/HTML view.
- Tests for core logic (aiming ~80%+ coverage) and user docs.

**Nice‑to‑have (stretch):**

- More templates and smarter label suggestions in the wizard.
- Real‑time updates (e.g. WebSockets) instead of page refresh.
- Deeper Project B integration (campaign‑scoped badges/rewards).

---

## Pros / cons

**Pros**

- Directly matches Founder Frank and Open Source Oliver’s pain: “I can’t just ‘do security’, give me a concrete push.”
- Low external dependencies: works today with issues + labels; enhanced (not blocked) by A/B.
- Adds a **“programs” layer** to BLT: “we ran 3 security campaigns this year” is a compelling story.
- Natural orchestration layer for other projects:
  - A can feed higher‑quality issues into campaigns,
  - B can reward campaign participation,
  - C/D can use recaps as educational/knowledge‑sharing material.

**Cons**

- Needs careful UX to keep the wizard simple, not overwhelming.
- Progress tracking can get subtle in noisy repos (changing labels/scope mid‑campaign).
- Without good templates and examples, campaigns could devolve into “just another list”.

---

## Why it fits GSoC

- Clear, self‑contained 350‑hour scope with a well‑defined MVP.
- Real, validated pain point from Discussion #5495: small projects and founders wanting concrete, time‑boxed security pushes.
- Complementary to, not competing with, existing ideas:
  - B rewards *what* was done,
  - **W organizes *how* and *when* it gets done**.

