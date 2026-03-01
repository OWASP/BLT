# BLT-CVE Federation Specification

## Overview

The BLT-CVE registry is designed to be federated. Other repositories and organizations can mirror, aggregate, and verify entries from this registry using the machine-readable index and feed files.

---

## 1. Federation Manifest

Each registry publishes a `/federation.json` file at its root:

```json
{
  "namespace": "BLT",
  "public_key": "TBD",
  "index_url": "https://owasp-blt.github.io/BLT-CVE/index.json",
  "feed_url": "https://owasp-blt.github.io/BLT-CVE/feed.json",
  "schema_url": "https://owasp-blt.github.io/BLT-CVE/schema/blt-cve-schema.json",
  "contact": "https://github.com/OWASP-BLT/BLT-CVE/issues"
}
```

| Field        | Description |
|--------------|-------------|
| `namespace`  | The ID prefix used by this registry (e.g., `BLT`) |
| `public_key` | PGP/Sigstore public key for verifying signed entries (TBD) |
| `index_url`  | URL of the machine-readable index |
| `feed_url`   | URL of the full metadata feed |
| `schema_url` | URL of the JSON schema |
| `contact`    | Where to report issues or abuse |

---

## 2. How to Mirror This Registry

To create a read-only mirror:

1. Fork `OWASP-BLT/BLT-CVE` on GitHub.
2. Enable GitHub Pages on the fork (deploy from `main` branch).
3. Set up a scheduled GitHub Actions workflow to `git pull` from upstream and push to the fork.
4. Publish your own `/federation.json` pointing to your mirror's URLs.

### Example Mirror Workflow

```yaml
name: Sync from upstream
on:
  schedule:
    - cron: '0 */6 * * *'
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Pull upstream
        run: |
          git remote add upstream https://github.com/OWASP-BLT/BLT-CVE.git
          git fetch upstream
          git merge upstream/main --ff-only
          git push origin main
```

---

## 3. How to Aggregate Entries

To aggregate entries from multiple registries into a unified view:

1. Fetch each registry's `/index.json`.
2. Prefix each entry's ID with its namespace to avoid collisions (e.g., `BLT:BLT-2026-0001`).
3. Fetch individual entry JSON files as needed.
4. Validate each entry against the registry's published schema.

### Namespace Collision Avoidance

When aggregating, always preserve the full `namespace:id` pair. Do not strip the namespace prefix.

---

## 4. How to Verify Signatures (Future)

Signature verification is planned using [Sigstore](https://sigstore.dev/). Once implemented:

1. Retrieve the registry's `public_key` from `/federation.json`.
2. For each entry, verify the `signature` field against the entry content.
3. Reject entries with invalid or missing signatures (in strict mode).

Until signatures are implemented, integrity is provided by GitHub's commit history and optional GPG-signed commits.

---

## 5. Implementing Your Own BLT-Compatible Registry

Any organization can implement a compatible registry by:

1. Forking this repository.
2. Replacing the `BLT` namespace with your own (e.g., `ACME`).
3. Updating `/federation.json` with your namespace and URLs.
4. Following the same schema and directory structure.
5. Publishing your registry on GitHub Pages.

Your registry's IDs will be `ACME-YYYY-NNNN` and will not conflict with BLT IDs.

---

## 6. Known Federated Registries

| Namespace | URL | Status |
|-----------|-----|--------|
| BLT       | https://owasp-blt.github.io/BLT-CVE/ | Active (canonical) |

To add your registry to this list, open a Pull Request updating this table.
