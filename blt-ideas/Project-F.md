Project F — Security Contributor Trust & Reputation Engine

One line: Explainable trust scoring for security contributors based on verified fixes, reviews, and historical accuracy.

Description:
Implements a security-first reputation graph that aggregates verified security contributions across BLT (PR fixes, reviews, remediation outcomes) and computes contributor trust scores. The system emphasizes signal quality over volume, weighting factors like fix correctness, severity impact, review usefulness, and false-positive rates. Provides maintainers with confidence signals for triage and delegation, and exposes read-only APIs for downstream systems (rewards, dashboards, education). Designed with opt-in visibility, auditability, and strong anti-gaming controls.