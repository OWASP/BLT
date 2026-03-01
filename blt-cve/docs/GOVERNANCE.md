# BLT-CVE Governance Model

## Overview

This document defines the governance model for the BLT vulnerability registry, including maintainer responsibilities, ID allocation policy, conflict resolution, abuse handling, and the disclosure policy.

---

## 1. Maintainers

The BLT-CVE registry is maintained by the OWASP BLT project maintainers. Maintainers are responsible for:

- Reviewing and merging vulnerability submissions.
- Ensuring entries comply with the schema and protocol.
- Allocating IDs sequentially without gaps or reuse.
- Handling disputes and abuse reports.
- Rotating signing keys as described in `SECURITY.md`.
- Publishing the governance model and keeping it up to date.

Current maintainers are listed in the repository's `CODEOWNERS` file (if present) or in the GitHub organization's team settings.

---

## 2. ID Allocation Policy

- IDs are allocated **sequentially** within each calendar year.
- The next available ID for year `YYYY` is `max(existing NNNN for YYYY) + 1`.
- Contributors **must not** pre-claim or reserve IDs; IDs are assigned at merge time.
- A maintainer assigns the final ID before merging a PR.
- Once merged, an ID is **permanent and immutable**.
- Deleted entries leave a tombstone comment or a stub file to prevent ID reuse.

---

## 3. Submission Process

1. Fork the repository.
2. Create a new file under `/cves/YYYY/BLT-YYYY-DRAFT.json` (use `DRAFT` as a placeholder).
3. Fill in all required fields per `/schema/blt-cve-schema.json`.
4. Open a Pull Request. The automated validator will check your entry.
5. A maintainer reviews the entry for accuracy and policy compliance.
6. The maintainer assigns the final sequential ID and renames the file.
7. The PR is merged and the index is regenerated automatically.

---

## 4. Conflict Resolution

- If two PRs submit entries for the same vulnerability, the first to be merged takes the ID; the second is asked to reference the first.
- Disputes about severity scores should be resolved by referencing the official CVSS calculator and linking evidence in the `references` array.
- Disputes between contributors are resolved by maintainer consensus. If maintainers cannot agree, the OWASP BLT project lead has final authority.

---

## 5. Abuse Handling

- Entries that contain false information, spam, or malicious content will be removed and the contributor may be banned from the repository.
- Removed entries leave a tombstone stub to prevent ID reuse.
- Abuse reports should be filed as GitHub Issues with the `abuse` label.

---

## 6. Disclosure Policy

- **Coordinated disclosure** is strongly encouraged. Reporters should notify affected vendors before submitting a public entry.
- A recommended embargo period is **90 days** from vendor notification.
- If a vendor is unresponsive after 90 days, the entry may be published.
- Entries for vulnerabilities with no available patch should include a mitigation section in the `description`.
- Entries for actively exploited vulnerabilities may be published immediately at maintainer discretion.

---

## 7. Relationship to Official CVE Program

BLT IDs are **not** MITRE-issued CVEs. This registry is an independent, community-operated namespace. When an official CVE is assigned for the same vulnerability, the BLT entry should be updated to include the CVE ID in the `references` array.

Contributors are encouraged to also submit vulnerabilities to MITRE's CVE Numbering Authorities (CNAs) for official CVE assignment.

---

## 8. Changes to This Document

Changes to the governance model require a PR with at least one maintainer approval. Major policy changes should be announced via a GitHub Discussion before merging.
