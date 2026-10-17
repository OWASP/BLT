# BLT-Zero (MVP Phase)

**Zero-Trust Vulnerability Reporting — encrypted payload delivery.**

BLT-Zero is a Cloudflare Workers site that lets security researchers submit sensitive vulnerability reports and screenshots **encrypted directly in the browser**. The Worker receives a pre-encrypted payload, forwards it directly to the organization’s security inbox, and stores only minimal metadata.

It is an independent application under the OWASP BLT project family, intended to run on its own deployment and database.

---

## 🔐 What is BLT-Zero?

BLT-Zero provides a secure workflow for delivering vulnerability reports:

- **Encryption happens client-side (browser)** using modern AES-256 ZIP encryption.
- **BLT-Zero never stores plaintext** vulnerability details.
- **Organizations decrypt locally** using standard archive tools.

### Key Principles

| Principle | Description |
|----------|-------------|
| **Encrypted Transit** | Worker receives only an encrypted ZIP package in Base64 (no plaintext files). |
| **Direct Delivery** | Reports are emailed directly to the organization's security team. |
| **No tracking by design** | No analytics/cookies/fingerprinting in this project. |
| **Abuse controls** | Rate limiting + optional Cloudflare Turnstile. |

---

## 🏗️ Architecture (Current MVP)

### Components

- **Client (Browser)**
  - Gathers the form data (Target URL, Description, Markdown) and dynamically builds a `report.json` in memory.
  - Bundles the JSON and uploaded screenshots using `@zip.js/zip.js`.
  - Generates a strong, random 24-character password and encrypts the ZIP file (AES-256) entirely inside the browser.
  - Sends the Base64-encoded encrypted ZIP and the generated password to the Worker.

- **Worker (Python / FastAPI)**
  - Validates request + (optional) Turnstile.
  - Emails the encrypted ZIP attachment and the decryption password to the org inbox via SendGrid.

---

## 🔒 Cryptography & Decryption

**Client-Side Encryption**
To ensure maximum compatibility and avoid requiring organizations to pre-generate PGP/JWK keys, encryption is handled via **AES-256 Password-Protected ZIPs**. The browser generates a secure, ephemeral password, encrypts the payload, and the Worker forwards this password to the organization alongside the file. 

**Decryption (Important Note for Windows Users)**
Because the browser uses modern AES-256 encryption, **the default Windows File Explorer cannot extract the ZIP file** (it will throw Error `0x80004005`). 

To decrypt the report, organizations must use a modern archive utility:
- **Windows:** Use [7-Zip](https://www.7-zip.org/) or WinRAR. Right-click -> Extract Here -> Enter the password from the email.
- **macOS:** Use The Unarchiver or the built-in Archive Utility.
- **Linux:** Use the `unzip` command-line tool.

---

## ✅ Features

- 🔒 Client-side ZIP encryption in the browser (`@zip.js`).
- 📧 Direct email delivery to org security inbox via SendGrid.
- 🧾 Minimal storage: domain + optional username + artifact hash only.
- 🛡️ Rate limiting to prevent abuse.
- 📊 Optional points sync to main BLT.

---

## 🚀 Workflow (end-to-end)

1. Reporter fills out the vulnerability form and attaches screenshots.
2. Browser intercepts the submission, generates a password, and bundles everything into an AES-256 encrypted ZIP.
3. Worker receives the encrypted Base64 string and the password.
4. Worker emails the ciphertext ZIP attachment + password to the org inbox.
5. Org receives the email, downloads the ZIP, and decrypts it locally using 7-Zip.

---

## 🛠️ Tech Stack

- Runtime: Cloudflare Workers (Python support)
- Frontend Crypto: `@zip.js/zip.js` (AES-256)
- Email: SendGrid
- Protection: optional Turnstile + rate limiting

---

### Installation

1. Clone the repository:
```bash
git clone [https://github.com/OWASP-BLT/BLT-Zero.git](https://github.com/OWASP-BLT/BLT-Zero.git)
cd BLT-Zero
```

2. Install Wrangler (if not already installed):
```bash
npm install -g wrangler
```

3. Login to Cloudflare:
```bash
wrangler login
```

4. Create `.dev.vars` file from `.dev.vars.example` and populate wrangler.toml with Database ID from previous step:

### Development

Run the development server:
```bash
wrangler dev
```

The application will be available at `http://localhost:8787`

### Deployment

Deploy to Cloudflare Workers:
```bash
wrangler deploy
```

### Org Onboarding (Keys)

1. Generate organization keypair locally:
```bash
python tools/org_keygen.py
```

This will generate:

- `private_key.jwk` (keep this secret)
- `public_key.jwk` (share this with BLT-Zero)

2. Decrypt a received vulnerability report:
```bash
python tools/org_decrypt.py private_key.jwk package.json
```

### Optional BLT points / BACON sync

BLT-Zero can **optionally** award BLT points/BACON for successful encrypted submissions
without ever sending plaintext report data to the main BLT platform.

- If the reporter supplies a `username` and you configure BLT sync, the Worker will
  POST a small JSON payload to the main BLT API:

  ```json
  { "username": "<reporter>", "domain_name": "<program domain>" }
  ```

- No report content, ciphertext, or fields derived from the encrypted package are sent.

To enable this integration:

1. Configure the following variables in `wrangler.toml` / `.dev.vars`:

   - `MAIN_BLT_API_URL` – base URL for the BLT API (defaults to `https://api.owaspblt.org`)
   - `MAIN_BLT_API_TOKEN` – BLT API token with permission to award points for Zero-Trust submissions

2. Deploy BLT-Zero with those values set.

If `MAIN_BLT_API_TOKEN` is not set, BLT sync is silently skipped and submissions
remain purely local to BLT-Zero.

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
