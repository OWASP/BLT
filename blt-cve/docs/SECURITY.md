# BLT-CVE Security Model

## Overview

This document describes the trust model, cryptographic integrity measures, maintainer key management, and revocation process for the BLT-CVE registry.

---

## 1. Trust Model

The BLT-CVE registry relies on the following layers of trust:

| Layer | Mechanism |
|-------|-----------|
| **Repository integrity** | GitHub branch protection + required PR reviews |
| **Contributor identity** | GitHub account authentication |
| **Commit signing** | GPG-signed commits (recommended for maintainers) |
| **Entry signing** | Sigstore integration (planned) |
| **Schema validation** | Automated CI check on every PR |

All entries are immutable once merged into `main`. GitHub's commit history provides an auditable log of all changes.

---

## 2. Branch Protection Requirements

The `main` branch must have the following protections enabled:

- Require pull request reviews before merging (minimum 1 reviewer).
- Require status checks to pass before merging (the `validate` workflow).
- Restrict who can push directly to `main` (maintainers only).
- Do not allow force pushes.
- Do not allow branch deletion.

---

## 3. GPG Commit Signing (Recommended)

Maintainers are strongly encouraged to sign their commits with a GPG key. Contributors may also sign commits.

To set up GPG signing:

```bash
gpg --gen-key
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
```

GitHub will display a "Verified" badge next to signed commits.

---

## 4. Sigstore Integration Plan

Future versions of this registry will use [Sigstore](https://sigstore.dev/) to provide entry-level cryptographic signatures:

1. When a maintainer merges a PR, a GitHub Actions workflow will sign the new entry JSON using `cosign`.
2. The resulting signature will be stored in the `signature` field of the entry.
3. Consumers can verify signatures using the registry's public key from `/federation.json`.
4. The Sigstore transparency log provides an additional audit trail.

This feature is tracked in the repository's issue tracker.

---

## 5. Maintainer Key Rotation

When a maintainer's signing key needs to be rotated:

1. The maintainer generates a new GPG key pair.
2. The new public key is added to the project's key roster (to be defined).
3. The old key is marked as revoked.
4. A signed announcement commit is made on `main` referencing the new key.
5. The `public_key` field in `/federation.json` is updated.

Key rotation does not invalidate previously signed entries; they remain valid under the old key.

---

## 6. Key Revocation

If a maintainer's key is compromised:

1. The maintainer (or another maintainer) immediately opens a GitHub Issue marked `security-critical`.
2. All entries signed with the compromised key are flagged for re-review.
3. The compromised key is revoked on the public key server and in the repository.
4. A new key is issued following the rotation procedure above.
5. Affected entries are re-signed by an uncompromised maintainer.

---

## 7. Reporting Security Issues in This Registry

To report a security issue **with the registry itself** (not a vulnerability submission):

- Open a private security advisory at: https://github.com/OWASP-BLT/BLT-CVE/security/advisories/new
- Or email the OWASP BLT maintainers directly.

Do **not** open public GitHub Issues for security issues affecting the registry's own integrity.

---

## 8. Disclaimer

BLT IDs are community-assigned and are **not** official MITRE CVE IDs. Always cross-reference with official sources for production security decisions. The registry makes no warranty of completeness or accuracy.
