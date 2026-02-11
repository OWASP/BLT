# Idea E — AI-Assisted Security Remediation Triage Platform (350h)

## Overview
A 350-hour development effort focused on providing advisory security triage for pull requests, helping contributors and maintainers identify and understand security-relevant changes and recommended remediation actions, without blocking merges or making authoritative vulnerability claims.  
The system analyzes pull request diffs, CI security signals, and repository context to surface medium-risk security hardening insights. Findings are presented via GitHub annotations and a BLT-hosted dashboard in a non-blocking, explainable format.

## Goals
- Analyze PR diffs to detect security-relevant changes
- Aggregate security-related CI signals:
  - SAST results
  - Secret scanning
  - Dependency vulnerability checks
  - Configuration and workflow analysis
- Detect common medium-risk security patterns, such as:
  - Unsafe token or environment variable handling
  - CI/CD workflow permission or injection risks
  - Insecure configuration defaults
  - Dependency risk exposure
- Correlate findings with specific files and changed lines
- Provide clear, contextual remediation guidance
- Present findings in a non-blocking advisory format
- Support both contributors and maintainers during code review

## Security Focus
- Deterministic, rule-based detection first
- Medium-risk, developer-focused hardening insights (not critical vulnerability scanning)
- Optional AI assistance for:
  - Improving explanation clarity
  - Providing remediation suggestions
  - Risk prioritization hints
- No automated enforcement
- No merge blocking
- No CVE generation or exploit storage
- Human-in-the-loop review encouraged

## GitHub Integration
- GitHub Checks API with neutral conclusion
- Inline annotations on affected lines
- Optional summarized PR advisory comment (non-authoritative)
- Ability to re-run analysis after updates or fixes

## Dashboard Capabilities
### Per-PR Advisory View
- List of detected security advisories
- Findings grouped by:
  - Category
  - Severity (Low / Medium)
  - Confidence level

### Contributor View
- What changed
- Why it matters from a security perspective
- Suggested remediation or safer alternative

### Maintainer View
- PRs with multiple or higher-risk advisories
- Repeated security patterns across contributors
- Repository-level security hardening trends

## Mockup
![Security Triage Dashboard Mockup](https://github.com/user-attachments/assets/b8fe3411-6223-499a-a8f1-aaaa5affb992)


> Illustrative mockup — final UX will evolve based on maintainer feedback.

## Week-by-Week Timeline (350h)

### Community Bonding (Weeks 1–2)
- Understand BLT workflows and security objectives
- Finalize detection scope and medium-risk categories
- Review existing CI and GitHub integrations
- Environment and development setup

### Phase 1 — Signal Ingestion
**Week 3**
- PR diff ingestion and parsing
- GitHub webhook handling
- CI/security check aggregation

**Week 4**
- Normalized security signal schema
- Baseline repository configuration and policies

### Phase 2 — Security Detection
**Week 5**
- Deterministic rule engine implementation
- Initial rules (config risks, secrets exposure, CI permissions)

**Week 6**
- File and line-level correlation
- Confidence scoring
- Severity classification (Low/Medium)

### Phase 3 — Remediation Guidance
**Week 7**
- Remediation hint templates
- Documentation and best-practice linking

**Week 8**
- Optional AI-assisted explanation layer
- Guardrails and opt-out controls

### Phase 4 — UX & Visibility
**Week 9**
- GitHub Checks integration
- Inline annotations

**Week 10**
- BLT dashboard MVP
- Filtering, grouping, and detail views

### Phase 5 — Quality & Scaling
**Week 11**
- False-positive reduction strategies
- Repository-level suppression or ignore rules

**Week 12**
- Performance optimization
- Caching and pagination

### Phase 6 — Polish & Handover
**Week 13**
- UX refinements based on feedback
- Contributor and maintainer documentation

**Week 14**
- Testing on real BLT repositories
- Bug fixes and stability improvements

**Week 15**
- Final feature refinements
- Deployment and configuration documentation

**Week 16**
- Final demo and evaluation
- Knowledge transfer and project handover

## Benefits
- Contributors receive clear, actionable security guidance during development
- Maintainers gain early visibility into potentially risky changes
- Reduces friction and uncertainty in security-related code reviews
- Encourages secure coding practices without interrupting workflow
- Establishes a foundation for future BLT security intelligence features

## Future Enhancements (Post-development)
- Learning from maintainer feedback to improve detection accuracy
- Expanded security pattern library
- Repository and organization-level security analytics
- Integration with other BLT security or verification pipelines
- SOC-style security visibility dashboards

## Risk Level
- Medium
- Advisory-only system (no enforcement complexity)
- Deterministic detection minimizes AI dependency
- Incremental architecture aligned with existing GitHub workflows

_Last Updated: February 2026_
