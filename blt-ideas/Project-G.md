NetGuardian: Distributed Autonomous Security Scanning & Validation Platform (GSoC 2026 -  350hr).

**Project Overview**
BLT-NetGuardian aims to become a practical, community-powered security scanning platform that helps identify real-world vulnerabilities while emphasizing accuracy, validation, and responsible disclosure.

**Core Objectives**
- Replace stubbed/demo scanners with real, verifiable vulnerability detection
- Introduce distributed scanning via a secure volunteer client
- Add result validation and false-positive filtering
- Benchmark scanner accuracy to ensure credibility
- Enable real autonomous discovery (CT logs, GitHub, blockchain)
- Improve disclosure workflows without leaking sensitive details

**Timeline**
- Phase 1 (Weeks 1–4 | ~120 hours)
  - Implement real vulnerability detection for:
  - Web application vulnerabilities (XSS, SQLi, CSRF, headers)
  - Static analysis using existing tools (e.g., Semgrep)
  - Normalize scanner outputs into a common result format
  - Add basic severity scoring and metadata
  - AI-assisted explanation layer (read-only):
    - Generate concise, human-readable explanations from scan findings
    - Convert raw findings into “what is wrong / why it matters” summaries
  - Deliverable: Working scanners producing real, structured vulnerability findings

- Phase 2 (Weeks 5–8 | ~120 hours)
  - NetGuardian Client & distributed scanning
  - Build a lightweight CLI client for volunteers
  - Enable task fetching, execution, and result submission
  - Integrate popular security tools (e.g., ZAP, Nuclei, Semgrep)
  - Add basic resource limits and scan controls.
  - Provide links to relevant OWASP guidance and best practices based on the findings.

- Phase 3 (Weeks 9–11 | ~90 hours)
  - Validation, accuracy & automation
  - Implement result validation and deduplication
  - Introduce consensus-based verification to reduce false positives
  - Add simple agent reputation scoring
  - Integrate real autonomous discovery sources (e.g., CT logs, GitHub metadata)
  - Improve responsible disclosure handling (security.txt, notifications)
  - Professional report with remedation recommendations.

**Benefits**
- Creates a solid foundation for long-term autonomous security monitoring.
- Founder with low budget can easily scan.
- Encourages responsible disclosure with controlled notifications.

