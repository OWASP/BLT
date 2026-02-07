### BLT Target Registry (Passive Directory of Security-Friendly Projects) (350 hours)

Repository: OWASP/BLT-NetGuardian

**Goal**

Build a safe, passive registry of projects, organizations, and domains that explicitly welcome bug reports — along with their disclosure policies and security contacts.

**Summary**

Transform the NetGuardian repository into a community-maintained Target Registry that aggregates publicly available disclosure information. Users can suggest targets, moderators verify details, and the system provides a searchable directory of projects that encourage responsible reporting. No scanning, probing, or recon — this is strictly metadata and documentation.

**Deliverables**
1. Target Submission Portal

- Allow users to submit GitHub repos, domains, or projects
- Form with policy URL, program details, optional tags

2. Moderator Validation Workflow

- Review queue for new submissions
- Verify disclosure policy/security.txt presence
- Approve/reject flow

3. Public Metadata Aggregation

- security.txt retrieval
- Disclosure policy link extraction
- Program name, scope, allowed reports
- Tags (e.g., "open-source", "webapp", "mobile", "library")

4. Target Registry UI

- Search and filters (tags, scope type, verification status)
- Project details page
- Disclosure instructions and policy link

5. Read-Only API

- Targets list endpoint
- Filter by category/scope
- JSON export for integrations

6. Documentation & Release

- Registry governance rules
- Contribution guide for moderators
- Public deployment