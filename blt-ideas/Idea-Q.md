# Toasty — AI Triage & Responsible Disclosure Assistant (2026 — 350 hours)

## development program Plan (4 × 4 weeks, 350 hours)

### Phase 1 (Weeks 1–4) — Foundations and Event Ingestion
**Goal:** Stand up Toasty as a reliable service wired to BLT/GitHub events; deliver safe, useful summaries early.

**Deliverables**
- Service + GitHub App/webhook ingestion for issue/PR create/edit and attachments.
- Summarizer v1: title + 3–5 bullets; label suggester (severity/category hints).
- Information-completeness checklists (missing steps, expected vs actual, environment).
- Initial PII/secret detectors (tokens, keys, JWTs, emails, URLs with secrets) with safe previews.
- Basic offline evaluation harness (golden set + quick metrics) and contributor docs.

**Acceptance**
- New issues/PRs receive: concise summary, suggested labels, missing info list, and any detected PII flagged.
- Latency/error rates stay within agreed targets.

---

### Phase 2 (Weeks 5–8) — Search, Semantic Dedup, and Repro Extraction
**Goal:** Reduce duplicate noise and extract actionable repro steps automatically.

**Deliverables**
- Embeddings pipeline + vector store; semantic search APIs.
- Cross-repo duplicate detection (issues + PRs) with confidence + brief rationale; “link potential duplicate” action.
- Reproduction-step extractor (steps, expected/actual, environment hints) and “Request more info” auto-prompts.
- Slack/CLI helpers:
  - on-demand safe summaries (`/toasty check <issue_url>`)
  - top-N duplicate candidates
- Robust job orchestration (batching, retries, basic back-pressure) for large repos.

**Acceptance**
- On a test corpus, top-3 duplicate suggestions meet target precision.
- Repro extractor yields structured steps reviewers can paste/apply.
- Slack/CLI responds within SLOs.

---

### Phase 3 (Weeks 9–12) — Reviewer Assist, Quality Tuning, and Safe Workflows
**Goal:** Make reviewers faster with calibrated, explainable suggestions and safe “apply” flows.

**Deliverables**
- Reviewer-assist snippets: risk synopsis, CWE/category hints, “ask-for-info” templates.
- Explainability: “why this label/duplicate” snippets referencing text/lines.
- Configurable org rules (labels/severity defaults, prompt tone, supported languages).
- Quality tuning: prompt iterations, context windowing, throttling/rate limits, guardrails and timeouts.
- Optional export-only API for signals so Project E (or others) can display them without Toasty owning readiness or dashboard UX.

**Acceptance**
- Side-by-side evaluation shows improved plan quality and fewer false positives.
- Reviewers can apply suggestions in one click with audit logs.
- Export-only API delivers signals without owning readiness.

---

### Phase 4 (Weeks 13–16) — Insights, Hardening, Docs, and Pilot Release
**Goal:** Prove measurable impact, harden for production, and pilot with real orgs.

**Deliverables**
- Lightweight “Toasty Insights” report (not a dashboard):
  - duplicate rate, estimated time saved, common gaps, top CWE/category
  - downloadable CSV/JSON
- Safety & robustness: adversarial inputs, size/time caps, abuse rate-limits; fallback paths when models fail.
- Offline evaluation suite:
  - dupe precision/recall
  - PII precision
  - summary quality rubric
  - release gates
- Documentation: reviewer/admin guides, runbooks, contribution guide; feature flags for staged rollout.
- Pilot with 1–2 orgs; post-pilot fixes; v1.0 tag and enablement checklist.

**Acceptance**
- Pilot shows ≥30% reviewer time reduction (median) and ≥0.80 dupe top-3 precision with zero critical incidents.
- Reports generated successfully; v1.0 signed off.

---

## Benefits
- **Faster triage with less noise:** Summaries, info-completeness checks, repro extraction, and semantic dedup reduce reviewer time and duplicate churn.
- **Safer collaboration:** PII/secret detectors prevent accidental leakage in summaries and Slack, while guardrails/rate limits keep the assistant reliable.
- **Complementary to Project E:** Toasty focuses on content assistance + optional signal export; Project E retains ownership of readiness states, CI/SAST aggregation, queues, and dashboard UX.
- **Measurable value:** An evaluation suite + pilot KPIs (time saved, dupe precision) make impact clear to mentors and orgs.

## Non-overlap with Project E (Extended) and Project H
- **Project E (Extended)** owns PR Readiness & Security Dashboard (readiness states, CI/SAST/secret/dependency aggregation, check annotations, maintainer queues, and dashboard UX). **Toasty does not** compute readiness states, aggregate CI, emit check annotations, or build/own a dashboard.
- **Project H** focuses on contributor growth (Sizzle time tracking, “what to work on next,” mentoring on PR merge). Toasty may optionally expose read-only signals that H can consume later, but **does not** implement time tracking or mentoring features.