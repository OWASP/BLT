**BLT Cybersecurity News API with Vulnerability Intelligence Dashboard and newsletter**

#### This project builds a BLT cybersecurity intelligence platform that transforms public CVEs, advisories, and security news into a personalized vulnerability intelligence dashboard, API, and newsletter for OWASP BLT users. Each vulnerability is presented as part of a broader security intelligence view—linking CVEs, advisories, and reported incidents to affected technology stacks, risk categories, and observed attack patterns. The platform helps users quickly understand what happened, who was impacted, and why it matters, without performing vulnerability detection, validation, or disclosure workflows. The focus is on situational awareness, visibility, and real-world context, enabling BLT users to track trends, recurring attack vectors, and ecosystem-level risk signals.

**Each vulnerability follows a three-step intelligence workflow:**
- Understand the vulnerability
(What CVE or advisory is this? What happened?)
- Contextualize the impact
(Affected stacks, attack type, severity, OWASP risk category, real-world incidents)
- Assess relevance
(Is this trending? Actively exploited? Relevant to specific ecosystems or projects?)

**Proposed Timeline**
- Phase 1 (Weeks 1–4 | ~90–100 hours)
  - Develop ui, Architecture, scope guardrails, and data ingestion foundations
  - Define strict post-disclosure scope and public-only data contracts
  - Set up backend architecture (API service, database, background jobs)
  - Implement ingestion framework for public sources:
  - CVE feeds
  - Security advisories
  - Public incident and breach reports
  - Add observability, logging, and ingestion health checks
  - Enforce separation from vulnerability detection or disclosure systems

- Phase 2 (Weeks 5–8 | ~120 hours)
   - Vulnerability intelligence processing and News API
   - Enrich vulnerabilities with:
   - Severity and exploit indicators
   - Affected technologies and ecosystems
   - Top 10 risk categorization
   - Implement trend and relevance scoring
       - Build Cybersecurity News API:
         - Filtered vulnerability feeds
         - Trending and high-impact views
         - Category- and stack-based queries
         - Provide API documentation for BLT Web and Flutter integration

- Phase 3 (Weeks 9–11 | ~110 hours)
   -  develop Vulnerability Intelligence Dashboard & Newsletter
   - Build Vulnerability Intelligence Dashboard:
   - Global vulnerability overview
   - Risk category breakdowns
   - Affected stack and ecosystem views
   - Trend and severity indicators
   - Implement newsletter system:
   - Weekly/monthly summaries
       - High-impact and trending vulnerabilities
   - User preference controls:
       - Topics, categories, frequency

- Phase 4 (Week 12 | ~20 hours)
  - End-to-end testing (ingestion → API → dashboard → newsletter)
  - Performance optimization and caching
  - Documentation and deployment guides

**Benefits**
 - Improves visibility into real-world vulnerabilities and security incidents
 - Helps users identify recurring attack patterns and high-risk ecosystems
 - Reduces noise by organizing large volumes of CVE data into meaningful views
 - Strengthens BLT as a security intelligence and awareness platform

**Future Extensions**
- Patch-adoption and ecosystem impact insights
- Webhooks or CLI tools for maintainers