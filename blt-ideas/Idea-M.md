# Project M — CVE Remediation Pipeline (sits on top of discovery from Project A and/or Project G (NetGuardian))

## Overview

**One line:** Full remediation lifecycle from discovery to AI-verified fix: consumes findings from discovery (performed by Project A and/or Project G (NetGuardian), or both) via webhooks, tracks merged fixes, verifies root cause is addressed and identifies related patterns, and emits verified remediation events to B.

**Project Type:** Single 350-hour development effort

**Note:** Discovery in the ideas list can be performed by **either Project A or Project G (NetGuardian), or both** — A and G overlap on discovery (scanner/GitHub → NVD vs. distributed scanning). Project M has a **different purpose**: it does _remediation_ only. M consumes findings from whichever discovery source(s) exist (A and/or G) via webhooks and manages the full lifecycle from discovered → merged → AI verified. The core value is fix quality and a remediation dashboard; M emits verified events to B.

**Primary Goal:** Bridge the gap between “vulnerability found” and “confidently fixed” by managing the remediation lifecycle, verifying that fixes truly resolve the CVE (and checking for related patterns elsewhere), and determining when a fix is ready to count as verified remediation for Project B (rewards).

---

## Problem Statement

- **Discovery vs. remediation:** Discovery is performed by Project A and/or Project G (NetGuardian), or both; there is no dedicated system to ensure fixes are correct, complete, and ready to count as verified remediation.
- **Fix quality uncertainty:** Merged PRs may not actually address root cause or may leave similar patterns elsewhere; manual verification does not scale.
- **Downstream rewards need verified signals:** Project B (rewards) needs a feed of _verified_ remediations, not just “PR merged” or “CVE mentioned.”

---

## Solution: CVE Remediation Pipeline

Project M **sits on top of discovery**. It does not do discovery; it consumes findings from discovery performed by **Project A and/or Project G (NetGuardian), or both** via webhooks and manages:

1. **Lifecycle:** discovered → (PR opened) → merged → AI verified → ready for B.
2. **AI verification:** Confirm the root cause is actually addressed; identify similar vulnerability patterns elsewhere; determine if the fix is complete.
3. **Remediation dashboard:** Maintainer view of remediation status, verification results, and related-pattern findings.
4. **Verified events to B:** Emit verified-remediation events so Project B can award rewards; M’s primary role is bridging “found” to “confidently fixed.”

---

## Relationship to Other Projects

| Project             | Role                   | Relationship to M                                                                                                                                                                              |
| ------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **NetGuardian (G)** | Discovery              | G performs discovery (distributed scanning). M consumes G’s findings via webhooks. M tracks and verifies remediation. Discovery can be performed by A or G or both.                            |
| **Project A**       | Detection & validation | A performs discovery (scanner/GitHub → NVD → GHSC). M consumes A's (and/or G's) findings via webhooks; M does remediation only. A and G can overlap on discovery; M works with either or both. |
| **Project E**       | Pre-merge readiness    | E focuses on CI, discussion, reviewer intent. M operates **post-merge**: did the fix truly resolve the CVE, are there related patterns, is it ready to count for B? No conflict.               |
| **Project B**       | Rewards                | M emits verified remediation events to B. B consumes M’s output; M does not implement BACON or leaderboards.                                                                                   |

---

## Technical Approach

### Data flow

1. **Discovery (Project A and/or Project G (NetGuardian), or both)** finds a vulnerability → sends finding via webhook to M.
2. **M** creates/updates a remediation record: status = discovered.
3. **PR linked** (e.g. via issue/PR association) → status = in progress.
4. **PR merged** → M triggers AI verification (async).
5. **AI verification:** Analyze fix (diff, context): root cause addressed? Similar patterns elsewhere? Completeness check.
6. **Remediation dashboard:** Maintainer sees status, AI summary, related patterns; can confirm or override.
7. **Verified** → M emits event to B (verified remediation); status = verified.

### Core components

- **Webhook ingestion:** Accept findings from discovery performed by Project A and/or Project G (NetGuardian), or both; normalize into remediation records.
- **Remediation model:** Track CVE/finding ID, repo, PR, status (discovered | in_progress | merged | verification_pending | verified | rejected), timestamps, AI verification result.
- **AI verification service:** Post-merge, analyze fix (e.g. diff, code context) to assess: root cause addressed, similar patterns elsewhere, completeness. Use Gemini free tier or local LLM; results advisory, human-in-the-loop via dashboard.
- **Remediation dashboard:** Maintainer view: list of remediations, status, AI summary, related patterns, actions (confirm verified, reject, request re-check).
- **Event emission to B:** When status = verified, emit event in the shape B expects (e.g. VerifiedSecurityContribution / verified remediation); B remains unchanged.

### Scope (350h)

- Webhook API and normalization (~40h).
- Remediation model, lifecycle state machine, PR linkage (~50h).
- AI verification (prompts, integration, result storage) (~70h).
- Remediation dashboard (UI, filters, actions) (~80h).
- Integration with B (event schema, emission) (~30h).
- Testing, docs, hardening (~80h).

---

## Differentiation

- **M vs. A and G:** A and G both do discovery (A = scanner/GitHub → NVD → GHSC; G = distributed scanning); they can overlap. M = remediation only; M consumes discovery from **either A or G or both** via webhooks. M does not do discovery.
- **M vs. E:** E = pre-merge (CI, discussion, reviewer intent). M = post-merge (fix correctness, related patterns, ready for B).

---

## Success Metrics

- Remediation records created from discovery webhooks (Project A and/or Project G (NetGuardian)); lifecycle states updated correctly.
- AI verification runs on merged PRs; results stored and shown in dashboard.
- Verified remediations emit to B; B can consume and award rewards.
- Maintainers use dashboard to confirm or override verification; time to “verified” tracked.

---

## Risks & Mitigations

| Risk                                          | Mitigation                                                                                  |
| --------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Discovery (A and/or G) webhook schema changes | Versioned webhook contract; adapter layer for normalization; M accepts from either or both. |
| AI verification false positives/negatives     | Human-in-the-loop on dashboard; maintainer confirm/override; iterate on prompts.            |
| Scope creep into discovery                    | Strict boundary: M consumes findings only; no scanning in M.                                |

---

## Why This Project Matters

1. **Fills the gap:** Discovery (performed by A and/or G) finds; M ensures fixes are real and complete before they count for rewards.
2. **Clear separation:** Discovery (A and/or G) vs. remediation (M) vs. pre-merge readiness (E) vs. rewards (B).
3. **Scalable fix quality:** AI verification plus dashboard scales better than manual-only verification.
4. **Single place for remediation:** One lifecycle and one dashboard from “found” to “verified for B.”

---

| Component                  | Notes                                                                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Discovery (A and/or G)** | Project A and/or Project G (NetGuardian) perform discovery; they can overlap. M consumes findings from either or both via webhooks. |
| **Project B**              | Consumes verified remediation events from M; no change to B's event shape required if M emits same schema as A would.               |
