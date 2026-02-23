# BLT-Zero

**Zero Trust Vulnerability Reporting — without a trace.**

BLT-Zero is a [Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/) powered site that lets security researchers report vulnerabilities directly and securely to target organizations — with **zero tracking** of sensitive data.

It is an independent application maintained under the [OWASP BLT](https://github.com/OWASP-BLT/BLT) project family, operating on its own infrastructure with no shared servers or database.

---

## 🔐 What is BLT-Zero?

BLT-Zero provides a **zero-trust workflow** for delivering vulnerability reports securely. Sensitive vulnerability details are **never stored** — they exist only in memory while the encrypted package is being built, then delivered directly to the recipient organization.

### Key Principles

| Principle | Description |
|-----------|-------------|
| **Direct Delivery** | Reports are encrypted with the recipient organization's public key so only they can decrypt them. |
| **Minimal Metadata** | Only non-sensitive metadata (e.g., domain name, username) and artifact hashes are stored — never vulnerability descriptions or PoC details. |
| **Ephemeral Handling** | Full vulnerability details exist only in memory or ephemeral Cloudflare Worker storage while building the encrypted package. Plaintext is never written to permanent storage. |
| **Out-of-Band Secrets** | Any symmetric passwords are delivered through a separate channel (phone, SMS, or secure messaging) and are never stored alongside report content. |

---

## 🏗️ Architecture

BLT-Zero runs entirely on **Cloudflare Workers** using Python, giving it:

- **No persistent server infrastructure** — serverless, edge-deployed execution.
- **Ephemeral worker storage** — sensitive data never survives beyond request processing.
- **Zero tracking** — no analytics, no fingerprinting, no user profiling.
- **Independent deployment** — its own domain and infrastructure, separate from the main BLT application.

### Encryption

Reports are encrypted using [age](https://age-encryption.org/) or OpenPGP with the recipient organization's public key. A symmetric password fallback is supported, delivered exclusively out-of-band.

---

## ✨ Features

- 🔒 End-to-end encrypted vulnerability report submission
- 📭 Direct delivery to recipient organizations — no middleman storage of sensitive data
- 🕵️ Zero tracking of reporters (no cookies, no analytics)
- 🗝️ Public-key encryption with optional symmetric password (out-of-band delivery)
- 📊 Minimal metadata storage for tracking, points, and program management
- 🔗 Integration with main BLT for reporter points attribution

---

## 🚀 How It Works

1. **Reporter** visits BLT-Zero and fills in the vulnerability report form.
2. The report is **encrypted in memory** using the target organization's public key.
3. The **encrypted package is delivered** directly to the organization — plaintext details are never persisted.
4. Only **minimal metadata** (domain, reporter username, artifact hash) is stored for points and tracking.
5. If a symmetric password is used, it is sent **out-of-band** by the reporter (e.g., via phone or secure messaging).

---

## 🛠️ Technology Stack

- **Runtime**: [Cloudflare Workers](https://workers.cloudflare.com/) (Python)
- **Encryption**: [age](https://age-encryption.org/) / OpenPGP
- **Storage**: Minimal — Cloudflare KV or D1 for non-sensitive metadata only
- **Integration**: OWASP BLT API for points attribution

---

## 🤝 Contributing

BLT-Zero is part of [OWASP BLT Project #79 — Zero Trust Vulnerability Reporting](https://github.com/OWASP-BLT/BLT-Zero/issues/1).

Contributions are welcome! Please:

1. Check the [open issues](https://github.com/OWASP-BLT/BLT-Zero/issues) for tasks to work on.
2. Fork the repository and create a feature branch.
3. Submit a pull request referencing the relevant issue.

Please follow the [OWASP BLT contribution guidelines](https://github.com/OWASP-BLT/BLT/blob/master/CONTRIBUTING.md).

---

## 📜 License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).
