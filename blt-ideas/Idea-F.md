## Project F — Contributor Security Reputation Graph (Quality-First Leaderboards)

**One line:** A quality-driven contributor reputation and leaderboard system that ranks trust and impact instead of raw activity.

**Description:**
BLT runs hackathons and pre-development programs where we repeatedly face issues with incorrect leaderboards, spam PRs, low-quality comments, and gaming of the system. Contributors often inflate scores by opening irrelevant issues, posting useless comments on PRs, or exploiting unclear scoring rules. The /leaderboard command and website leaderboards also suffer from incorrect timeline windows, inconsistent data, and a heavy focus on quantity over quality, with little guidance around best practices, code of conduct, or what actually makes a good contribution.

This project proposes a proper, long-term fix to these problems.

The system introduces a Contributor Security Reputation Graph that evaluates contributors based on quality signals, not volume. Signals can include accepted PRs, severity and impact of fixes, review usefulness, false-positive history, maintainer feedback, and sustained contribution behavior over time. Spam actions, low-effort comments, and irrelevant activity naturally decay or carry little weight.

###  Problem (Why this project exists)

BLT runs hackathons and pre-development programs, but we repeatedly face the same issues:

* Incorrect leaderboards
* Spam PRs and irrelevant issue creation
* Low-quality or useless comments just to gain points
* Gaming the system by focusing on quantity instead of quality
* Core BLT leaderboards showing wrong time windows and inconsistent data
* No clear definition of what counts as a *good contribution*

BLT-Hackathon partially solves this, but:

* it is separate from core BLT
* logic is not reusable
* quality signals are limited
* scoring rules are hard to explain

This causes confusion for contributors and extra work for maintainers.

---

###  Proposed Solution (What we build)

Build a **standalone, cloneable microservice** that evaluates contributors based on **quality, trust, and impact**, not raw activity.

Instead of counting:

* number of PRs
* number of comments
* number of issues

the system scores contributors using **quality signals**, such as:

* accepted vs rejected PRs
* severity or impact of fixes
* review usefulness
* maintainer feedback
* repeated false positives or spam behavior
* consistency of contributions over time

Low-effort or spam actions naturally decay or carry little weight.

This enables **leaderboards that rank quality, not quantity**.

---

###  Why standalone (important)

This project is built as a **standalone app**:

* Frontend: static web app (GitHub Pages)
* Backend: Python Cloudflare Worker

Why this matters:

* Can replace **BLT-Hackathon** entirely
* Can be used by **core BLT**
* Can be cloned and reused by other communities
* Avoids tight coupling with core BLT
* Reduces long-term maintenance cost

BLT consumes it as a service instead of maintaining multiple scoring systems.

---

###  How BLT-Hackathon + Core BLT become ONE system

Instead of:

* BLT-Hackathon leaderboard logic
* Core BLT leaderboard logic

We unify scoring into **one reputation engine**:

* BLT-Hackathon uses this service for scoring
* Core BLT uses the same service

This removes duplicate logic and keeps the scope manageable.

---

###  Core Features (In Scope)

* Contributor reputation graph (simple, explainable)
* Quality-weighted scoring engine
* Time-bounded leaderboards (hackathon, monthly, custom)
* Spam and low-quality signal decay
* Clear and documented scoring rules
* REST APIs for BLT and UI
* Simple admin configuration (weights, windows)

---

###  Phased Timeline (350h)

####  Phase 1 — Foundations (Weeks 1–2)

* Finalize requirements and scope
* Define quality signals
* Design scoring rules and decay logic

####  Phase 2 — Data & Scoring Engine (Weeks 3–4)

* GitHub API ingestion
* Core data models
* Scoring engine v1
* Time-window handling

#### Phase 3 — Reputation & Anti-Gaming (Weeks 5–6)

* Reputation graph logic
* Spam and decay mechanisms
* Edge-case handling

#### Phase 4 — APIs & Dashboard (Weeks 7–8)

* REST APIs
* Frontend dashboard v1
* Leaderboard and contributor views

#### Phase 5 — Integration & Hardening (Weeks 9–10)

* Integration with BLT-Hackathon and core BLT
* Performance and API limits handling
* Testing with real data

#### Phase 6 — Documentation & Delivery (Weeks 11–12)

* Documentation and usage guides
* Scoring explanation docs
* Final polish and mentor review

####  Mock up 
<img width="1152" height="707" alt="mock-up" src="https://github.com/user-attachments/assets/cf3839dd-2fe0-4605-9977-ff3f454afa1d" />