# Project X — RepoTrust Score

## One line

A single, explainable 0–100 security-health score for OSS repos that founders can use to choose dependencies and maintainers can use to see "how we're doing" and what to fix next.

---

## Problem & personas

- **Founder Frank (small startup founder)** needs to pick dependencies but has no simple way to compare "is this repo getting safer over time?"
- **Open Source Oliver (maintainer)** wants a clear, fair signal of their repo's security posture and concrete next steps—not just a list of issues.

Today BLT has issues, rewards, and education, but there's **no one number** that summarizes "this repo's security health" in a way that's transparent and actionable. RepoTrust Score turns BLT's events into a FICO‑like, explainable score with a "why" breakdown and a "how to improve" checklist.

---

## Core idea

A **RepoTrust Score** (0–100) computed from six transparent signals over a rolling window (e.g. 180 days):

1. **Time to remediate (TTR)** — median days to fix High/Critical security issues.
2. **Outstanding severity** — count and age‑weight of open Critical/High items.
3. **Verified-fix ratio** — verified security fixes / total security issues (GHSC or CVE/GHSA‑linked when available).
4. **Release recency** — time since last stable release.
5. **Dependency health** — share of direct deps with unresolved advisories (OSV/GHSA/NVD/Dependabot).
6. **Maintainer responsiveness** — median time to first response on security‑labeled issues/PRs.

Each signal is normalized to 0–100 (100 = best); the score is a weighted sum with published weights. A **confidence** value (0–1) reflects sample size; low data is labeled **"Provisional"**. Repos must **opt in**; scores are recomputed nightly. No popularity metrics, no private data, no cross‑org shaming—just public, explainable signals and actionable guidance.

---

## Data model (sketch)

```text
RepoTrustSnapshot
  - repo (FK → Repo)
  - score (0–100)
  - confidence (0–1)
  - components (JSON: ttr, outstanding, verified_fix_ratio, release_recency, dep_health, responsiveness)
  - sample_sizes (JSON: fixes_last_180d, security_issues_last_180d, …)
  - computed_at
  - version (for formula/weights)

RepoTrustEnrollment  (opt-in)
  - repo (FK → Repo)
  - enrolled_at
  - public_display (bool; per-repo toggle)
  - opted_out_at (null until opt-out)
```

Weights (example, sum = 1.0): TTR 0.30, Outstanding 0.20, Verified-fix ratio 0.20, Release recency 0.10, Dependency health 0.10, Responsiveness 0.10. Formulas and weights are published; every score has a "why" breakdown.

---

## API surface (sketch)

- `GET /api/v1/repos/{id}/repo-trust` — current snapshot (score, confidence, components, weights, sample_sizes, label e.g. "Good (Provisional)").
- `GET /api/v1/repos/{id}/repo-trust/history` — last N snapshots (for trend sparkline).
- `GET /api/v1/repo-trust?owner=O&name=R` — lookup by slug.

Auth: existing Django session + CSRF; only enrolled repos return data. Org‑scoped permissions for enrollment/opt-out.

---

## UX flows

### Founder / dependency consumer

- Look up a repo (by slug or from BLT repo page).
- See score badge + trend arrow; click "Why?" for component breakdown and "how to improve" hints (e.g. "Reduce TTR: aim fix &lt;30 days", "Close 2 high-severity items to reach 80", "Cut vulnerable deps by upgrading X/Y").

### Maintainer

- Enroll repo in RepoTrust (opt-in).
- On repo page: score gauge, trend over 90 days, "What changed last week?".
- Use checklist to prioritize improvements; optionally toggle public display of score.

---

## Policy & governance (ready-to-paste)

- **Scope:** RepoTrust is an explainable, opt-in 0–100 score per repo using public data and verified-fix events. No private GitHub data.
- **Signals (v1):** TTR (High/Critical), age-weighted backlog (High/Critical), verified-fix ratio, release recency, dependency health, security responsiveness, and a confidence score.
- **Exclusions (v1):** popularity metrics, language/framework, code churn, private GHAS status, broad static counts without context.
- **Transparency:** Publish formulas/weights; show per-repo "why" breakdown and actionable guidance; label low-sample snapshots as "Provisional".
- **Privacy & governance:** Opt-in only; per-repo toggle for public display; no cross-org leaderboard by default; easy opt-out and snapshot deletion; adhere to platform TOS. RepoTrust does not gate BLT participation or rewards.

---

## Integration points

- **Repos / orgs:** reuse existing `Repo`, `Organization`; enrollment and snapshot storage in `website/security/` (e.g. `repo_trust.py`).
- **Signals:** issue/PR lifecycle, release tags, GHSC/verified events (Project A when available), OSV/GHSA/Dependabot for dependency health.
- **UI:** repo header badge, "Why?" modal, optional "top improving repos" for org (no cross-org leaderboard).
- **Nightly:** management command to recompute snapshots for enrolled repos only.

---

## development program scope (350h)

**Must-have (MVP):**

- RepoTrustSnapshot (and optional RepoTrustEnrollment) models + migrations.
- Six normalizers + default weights + score computation with confidence.
- Nightly batch job (mgmt command) for enrolled repos.
- REST API: current snapshot + history.
- Repo page: score gauge, trend, "Why?" breakdown, "how to improve" checklist.
- Opt-in enrollment + opt-out / data deletion; methodology disclaimer in UI.
- Tests for core logic (~80%+ coverage) and user docs.
- Pilot with 10–15 repos across 3+ orgs; tune thresholds/weights with maintainers.

**Nice-to-have (stretch):**

- Optional "security automation" signal (e.g. CodeQL workflow, dependabot.yml) at low weight.
- Stretch metric: % of pilot repos that adopt at least one suggested improvement (self-reported).

---

## Evaluation metrics (for development program)

- **Adoption:** ≥10–15 opt-in repos across 3+ orgs with snapshots and breakdowns.
- **Usefulness:** Maintainer rating ≥4/5 on "The guidance (breakdown + 'how to improve') is actionable."
- **Accuracy (optional):** In ≥80% of sampled pairs, the higher RepoTrust score aligns with mentor/maintainer judgment of "better security posture" over the same window.

---

## Pros / cons

**Pros**

- Directly serves Founder Frank ("which dependency?") and Open Source Oliver ("how are we doing?").
- Works today with basic signals; gets stronger when Project A's verified-fix pipeline exists.
- Explainable and fair: published weights, no popularity, no cross-org shaming.
- Natural building block for a future Founder Dashboard / Command Center; complements B (e.g. "top improving repos").

**Cons**

- Reputation risk if misunderstood—mitigated by opt-in, confidence labels, and clear methodology.
- Sparse data for new/small repos ("Provisional" label and leaning on recency/dep health until events accumulate).
- Gaming possible in theory—mitigated by verified events, rolling windows, and caps.

---

## Why it fits development program

- Focused, standalone scope: model + ETL + nightly job + API + minimal UI + pilot. Not the full dashboard—just the score and its plumbing.
- Clear MVP and success criteria; 350h is enough to nail methodology, correctness, and adoption.
- Fits Discussion #5495: helps small projects and founders make dependency and security-health decisions with one actionable number.
