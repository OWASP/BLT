# BLT-CVE: Decentralized, Federated Vulnerability Registry

A standards-driven, machine-readable, cryptographically verifiable, federated vulnerability namespace that runs entirely on **GitHub Pages** and **GitHub Actions** — no backend required.

> ⚠️ BLT IDs are **not** MITRE-issued CVE IDs. They are community-assigned identifiers within the OWASP BLT ecosystem. Always cross-reference with official CVE sources for production security decisions.

---

## 🎯 Purpose

- Provide a community-operated vulnerability registry under the `BLT` namespace.
- Store all data as static JSON, served from GitHub Pages.
- Enable automated validation and index generation via GitHub Actions.
- Support federation so other organizations can mirror or aggregate entries.
- Remain entirely forkable and server-free.

---

## 📋 Namespace Format

Vulnerability IDs follow the format:

```
BLT-YYYY-NNNN
```

| Component | Description |
|-----------|-------------|
| `BLT`     | Fixed namespace prefix |
| `YYYY`    | Four-digit year of publication |
| `NNNN`    | Zero-padded sequential number |

Example: `BLT-2026-0001`

---

## 📁 Repository Structure

```
/cves/
  /2026/
    BLT-2026-0001.json      ← individual vulnerability entries
/schema/
  blt-cve-schema.json       ← JSON schema for entries
/index.json                 ← machine-readable master index
/feed.json                  ← full metadata feed
/federation.json            ← federation manifest
/docs/
  PROTOCOL.md               ← data format & ID rules
  GOVERNANCE.md             ← maintainer & disclosure policy
  FEDERATION.md             ← how to mirror/aggregate
  SECURITY.md               ← trust model & key management
/scripts/
  validate_cves.py          ← local validation script
  build_index.py            ← regenerates index.json & feed.json
.github/workflows/
  validate.yml              ← PR validation workflow
  build-index.yml           ← auto-regenerate index on merge
```

---

## 📤 How to Submit a Vulnerability

1. **Fork** this repository.
2. Create a new file: `cves/YYYY/BLT-YYYY-DRAFT.json` (use `DRAFT` as a placeholder ID).
3. Fill in all required fields following the schema in `/schema/blt-cve-schema.json`.
4. Run local validation:
   ```bash
   pip install jsonschema
   python scripts/validate_cves.py
   ```
5. **Open a Pull Request**. The automated validator will check your entry.
6. A maintainer will assign the final sequential ID, rename the file, and merge.
7. The index is regenerated automatically after merge.

### Entry Format

```json
{
  "id": "BLT-2026-0001",
  "published": "2026-02-22T00:00:00Z",
  "modified": "2026-02-22T00:00:00Z",
  "title": "Short vulnerability summary",
  "description": "Full technical description of the vulnerability",
  "affected": [
    {
      "vendor": "ExampleCorp",
      "product": "ExampleApp",
      "versions": "1.0.0 through 1.2.3"
    }
  ],
  "severity": {
    "cvss_score": 9.8,
    "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
  },
  "references": [
    "https://example.com/advisory/2026-001"
  ],
  "reporter": "your-github-username",
  "signature": ""
}
```

---

## ✅ Validation Requirements

Every entry must:

- Conform to `/schema/blt-cve-schema.json`.
- Have an `id` that matches the filename (`BLT-YYYY-NNNN.json`).
- Have a year in the `id` that matches its parent folder (`cves/YYYY/`).
- Have a unique `id` across the entire registry.
- Include all required fields: `id`, `published`, `modified`, `title`, `description`, `affected`, `severity`, `references`, `reporter`.

The `validate.yml` GitHub Actions workflow enforces these rules on every PR.

---

## 🌐 Machine-Readable Endpoints (GitHub Pages)

| URL | Description |
|-----|-------------|
| `/index.json` | Lightweight master index with ID, path, and severity |
| `/feed.json` | Full metadata feed with titles and dates |
| `/federation.json` | Federation manifest for mirrors/aggregators |
| `/schema/blt-cve-schema.json` | JSON schema for entries |
| `/cves/YYYY/BLT-YYYY-NNNN.json` | Individual vulnerability entries |

---

## 🔗 Federation

Other organizations can mirror or aggregate this registry. See [docs/FEDERATION.md](docs/FEDERATION.md) for details, including:

- How to set up a mirror.
- How to aggregate entries from multiple registries.
- How to implement a compatible registry under your own namespace.

---

## 🔐 Security & Governance

- [docs/SECURITY.md](docs/SECURITY.md) — trust model, GPG signing, Sigstore plan, key rotation.
- [docs/GOVERNANCE.md](docs/GOVERNANCE.md) — maintainer responsibilities, disclosure policy, abuse handling.
- [docs/PROTOCOL.md](docs/PROTOCOL.md) — full protocol specification.

---

## 🆚 Difference from Official CVE Program

| Aspect | MITRE CVE | BLT-CVE |
|--------|-----------|---------|
| Authority | MITRE / CNAs | OWASP BLT community |
| ID format | CVE-YYYY-NNNNN | BLT-YYYY-NNNN |
| Infrastructure | Centralized | GitHub Pages (static) |
| Forkable | No | Yes |
| Backend required | Yes | No |

BLT IDs complement, rather than replace, the official CVE system. When an official CVE is assigned, the BLT entry should reference it.

---

## 📝 License

This project is licensed under the terms included in the [LICENSE](LICENSE) file.

## 🌐 OWASP BLT

This project is part of the OWASP BLT initiative. Visit [BLT Website](https://owasp.org/www-project-buglogging-tool/) for more information.
