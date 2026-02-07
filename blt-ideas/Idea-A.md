### Idea A — CVE Detection & Validation Pipeline

**One line:** Opt-in pipeline from scanner/GitHub → NVD validation → GHSC model and verification UI/API.

**Description:** Discovers CVE-related contributions from webhooks and scanner output (e.g. Buttercup), validates against NVD, deduplicates and scores findings, and exposes them via a maintainer verification dashboard and REST API. Post-disclosure only; no raw exploit storage. Foundation for downstream rewards and education.
