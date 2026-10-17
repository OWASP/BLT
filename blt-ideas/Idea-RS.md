# Idea RS — Report Signal Intelligence & Pre-Triage Assistant (175h)

## Overview
A development effort focused on assisting human triagers by surfacing report quality signals before manual review.

BLT currently depends heavily on reporter-provided information prior to triage. Reviewers must manually determine report credibility, relevance, and effort level, which introduces fatigue and inconsistent reward decisions.

This project introduces a pre-triage intelligence layer that analyzes report structure, metadata, and technical patterns to generate assistive signals.

The system does NOT reject reports or validate vulnerabilities.  
It only improves reviewer awareness.

---

## Key Differentiation

This project does not:
- detect vulnerabilities
- perform automated security judgement
- block report submissions

Instead it:
- evaluates report quality characteristics
- highlights suspicious or low-effort patterns
- provides context for faster human decisions

It acts as an intake quality layer before triage.

---

## Goals

### Pre-Triage Signal Engine
Generate explainable signals such as:

- Possible duplicate report
- Likely automated scanner output
- Insufficient reproduction clarity
- Severity claim mismatch
- Suspicious payload structure

Signals are advisory only.

---

### Metadata Consistency Analysis
Detect logical inconsistencies:

- Target does not match payload
- Incorrect vulnerability category
- Missing technical explanation
- Unrealistic severity vs evidence

---

### Low-Effort & Noise Detection
Identify patterns correlated with noisy submissions:

- repeated templates
- extremely high submission frequency
- copied reports across accounts
- empty or generic PoCs

---

### Technical Structure Analysis
Evaluate report structure quality:

- raw scanner dump pasted
- non-executable proof-of-concept
- random fuzzing without reasoning
- vulnerability class mismatch

---

## Triage Interface Capabilities

### Reviewer View
Display signal hints:

- ⚠ Severity likely overstated
- ⚠ Possible duplicate payload
- ⚠ Likely automated submission
- ⚠ Reproduction unclear

Each signal includes explanation text.

---

### Confidence Indicators
Signals categorized as:

- Informational
- Suspicious
- High Noise Risk

No automated enforcement.

---

## Implementation Approach

### Phase 1 — Rule-Based Signals
- deterministic heuristics
- explainable outputs

### Phase 2 — Signal Scoring
- weighted signal confidence
- aggregated report quality score

### Phase 3 — Adaptive Learning (Optional)
- clustering similar reports
- dynamic noise pattern updates

---

## OWASP Alignment

Supports secure disclosure workflows by:

- reducing triage fatigue
- improving reward fairness
- preventing reviewer oversight due to noise
- keeping humans in control of judgement

Important:
- no vulnerability validation
- no CVE generation
- no automated rejection

---

## Week-by-Week Timeline (175h)

### Community Bonding (Week 1)
- understand report lifecycle
- define signal taxonomy

### Phase 1 — Foundations
**Week 2**
- report parsing & metadata extraction

**Week 3**
- rule-based signal engine

### Phase 2 — Signal Intelligence
**Week 4**
- consistency analysis

**Week 5**
- duplicate & spam heuristics

### Phase 3 — Reviewer Interface
**Week 6**
- triage UI hints
- explanation messages

### Phase 4 — Scoring Layer
**Week 7**
- signal aggregation score

### Phase 5 — Testing & Refinement
**Week 8**
- real report validation
- tuning false positives

### Phase 6 — Documentation
**Week 9**
- contributor docs
- maintainer usage guide

---

## Benefits

- faster triage decisions
- improved reviewer confidence
- fairer rewards
- scalable moderation

---

## Future Enhancements

- ML clustering of similar reports
- reporter reputation scoring integration
- adaptive noise filtering

