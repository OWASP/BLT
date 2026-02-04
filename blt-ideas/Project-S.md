### BLT-CVE Explorer & Resilient Multi-Source CVE Mirror (350 hours)

Repository: OWASP/BLT-CVE

**Goal**

Provide a fast, reliable CVE explorer and mirror service that aggregates CVE data from multiple public sources and makes it searchable, browsable, and usable across BLT.

**Summary**

Implement a CVE aggregation and explorer system that syncs CVE data from public feeds (e.g., NVD, GitHub Advisory), caches it efficiently, and exposes a unified search and browsing interface. Add autocomplete, package filters, watchlists, and optional community notes with moderation controls. This improves contributors' ability to reference CVEs and enriches BLT workflows.

**Deliverables**
1. Multi-Source CVE Sync

- Scheduled importer for NVD JSON feeds
- GitHub Advisory sync
- Local caching + rate limit protection
- Update tracking

2. High-Speed Search & Autocomplete

- Prefix search for CVE IDs
- Filters: year, severity, vendor, product
- Fast autocomplete endpoint for forms

3. CVE Explorer UI

- Search bar
- Detailed CVE page with CVSS data, references, affected packages
- Severity color coding
- Related CVEs list

4. Watchlists & Notifications

- Follow specific CVEs or packages
- Email/notification support for updates

5. Community Notes (Moderated)

- Users can add remediation tips, explanations
- Moderation queue before publishing

6. Export Tools

- JSON / CSV export
- “Offline bundle” generation

7. Audit Logging

- Track all changes, imports, notes
- Immutability through a simple audit log model

8. Documentation

- Data model reference
- Sync schedule guide
- Contribution guidelines