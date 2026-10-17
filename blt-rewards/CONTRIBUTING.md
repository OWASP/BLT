# Contributing to BLT-Rewards (BACON)

Thank you for your interest in contributing to **BACON — Blockchain Assisted Contribution Network**! This guide will get you from zero to a working local setup, and walk you through everything you need to know before opening your first PR.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Setup](#local-setup)
3. [Environment Variables](#environment-variables)
4. [Running the Project](#running-the-project)
5. [Project Structure](#project-structure)
6. [Making Changes](#making-changes)
7. [Opening a Pull Request](#opening-a-pull-request)
8. [Reporting Issues](#reporting-issues)
9. [Code of Conduct](#code-of-conduct)

---

## Prerequisites

Make sure the following are installed on your machine before you start:

| Tool | Version | Why |
|---|---|---|
| [Node.js](https://nodejs.org/) | v18 or higher | Runs Wrangler CLI |
| [npm](https://www.npmjs.com/) | Bundled with Node.js | Installs dependencies |
| [Python](https://www.python.org/downloads/) | 3.10 or higher | Local testing of Worker logic and ord-server |
| [Git](https://git-scm.com/) | Latest | Version control |
| [Cloudflare Account](https://dash.cloudflare.com/sign-up) | Free tier works | Required to deploy and manage Workers |
| [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/) | Installed via npm | Cloudflare Workers development tool |

> **Tip:** Run `node -v`, `python --version`, and `git --version` to confirm versions are correct before proceeding.

---

## Local Setup

### 1. Fork & Clone the Repository

First, fork the repo on GitHub, then clone your fork locally:

```bash
git clone https://github.com/<your-username>/BLT-Rewards.git
cd BLT-Rewards
```

Add the upstream remote so you can pull in future changes:

```bash
git remote add upstream https://github.com/OWASP-BLT/BLT-Rewards.git
```

### 2. Install Node Dependencies

```bash
npm install
```

This installs [Wrangler](https://developers.cloudflare.com/workers/wrangler/), which is the only Node dependency required for this project.

### 3. Set Up Python Environment (for ord-server)

The `ord-server/` component is a Python Flask application. Set up a virtual environment for it:

```bash
# From the project root
python -m venv .venv

# Activate it:
# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Install ord-server dependencies
pip install -r ord-server/requirements.txt
```

### 4. Configure Environment Variables

See the [Environment Variables](#environment-variables) section below — this is the most important step before running anything.

### 5. Authenticate with Cloudflare (Wrangler)

```bash
npx wrangler login
```

This opens a browser window to authenticate your Cloudflare account. You only need to do this once.

---

## Environment Variables

The project uses two separate `.env.example` files — one for the Cloudflare Worker and one for the ord-server.

### Step 1 — Root `.env` (Cloudflare Worker)

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

| Variable | Description | Where to find it |
|---|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | Your Cloudflare account ID | [Cloudflare Dashboard](https://dash.cloudflare.com/) → Right sidebar |
| `WRANGLER_API_TOKEN` | API token for non-interactive Wrangler auth (optional) | Cloudflare Dashboard → My Profile → API Tokens |
| `BITCOIN_RPC_URL` | URL of your Bitcoin node RPC endpoint | Your Bitcoin node config (`bitcoin.conf`) |
| `BITCOIN_RPC_USER` | RPC username for your Bitcoin node | Your `bitcoin.conf` |
| `BITCOIN_RPC_PASSWORD` | RPC password for your Bitcoin node | Your `bitcoin.conf` |
| `SOLANA_RPC_URL` | Solana RPC endpoint (e.g. `https://api.mainnet-beta.solana.com`) | [Solana docs](https://docs.solana.com/cluster/rpc-endpoints) or your RPC provider |
| `SOLANA_WALLET_ADDRESS` | Your Solana wallet public key | Your Solana wallet |
| `GITHUB_TOKEN` | Personal access token for GitHub Actions integration | GitHub → Settings → Developer Settings → Tokens |

### Step 2 — Wrangler Variables (`wrangler.toml`)

These are non-secret configuration values already in `wrangler.toml`. Update them as needed:

| Variable | Description |
|---|---|
| `ENVIRONMENT` | Deployment environment (`production` or `development`) |

### Step 3 — ord-server `.env` (Bitcoin Ordinals Server)

```bash
cp ord-server/.env.example ord-server/.env
```

Open `ord-server/.env` and fill in your values:

| Variable | Description |
|---|---|
| `ORD_PATH` | Absolute path to the `ord` binary on your machine |
| `YAML_FILE_PATH` | Temp YAML file path used during batch processing |
| `BITCOIN_RPC_USER_MAINNET` | Mainnet Bitcoin node RPC username |
| `BITCOIN_RPC_PASSWORD_MAINNET` | Mainnet Bitcoin node RPC password |
| `BITCOIN_RPC_URL_MAINNET` | Mainnet Bitcoin node RPC URL |
| `BITCOIN_DATADIR_MAINNET` | Mainnet Bitcoin data directory path |
| `BITCOIN_RPC_USER_REGTEST` | Regtest Bitcoin node RPC username |
| `BITCOIN_RPC_PASSWORD_REGTEST` | Regtest Bitcoin node RPC password |
| `BITCOIN_RPC_URL_REGTEST` | Regtest Bitcoin node RPC URL |
| `BITCOIN_DATADIR_REGTEST` | Regtest Bitcoin data directory path |
| `ORD_SERVER_URL_MAINNET` | URL of your mainnet ord server |
| `ORD_SERVER_URL_REGTEST` | URL of your regtest ord server |
| `WALLET_NAME_MAINNET` | Mainnet wallet name |
| `WALLET_NAME_REGTEST` | Regtest wallet name |
| `WALLET_ADDRESS_REGTEST` | Regtest wallet address |
| `WALLET_API_PASSWORD` | Wallet API password |
| `FLASK_PORT` | Port for the Flask ord-server (default: `9002`) |

> **Note:** You don't need the ord-server running for basic Cloudflare Worker development. It's only needed for Bitcoin Ordinals / Runes-specific features.

---

## Running the Project

### Start the Cloudflare Worker (local dev)

```bash
npm run dev
```

This starts Wrangler's local development server. The worker will be accessible at `http://localhost:8787`.

Hot reload is enabled, so any changes to `src/` are reflected immediately.

### Start the ord-server (optional)

```bash
# Ensure your venv is activated first
cd ord-server
python ord-api.py
```

The Flask server will start on the port defined by `FLASK_PORT` in your `ord-server/.env` (default: `9002`).

### Available npm Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start local development server |
| `npm run deploy` | Deploy to Cloudflare Workers (production) |
| `npm run deploy:dev` | Deploy to Cloudflare Workers (dev environment) |

---

## Project Structure

```
BLT-Rewards/
├── .env.example            # Root environment variables template
├── .gitignore
├── LICENSE
├── package.json            # Node.js dependencies (Wrangler)
├── README.md
├── CONTRIBUTING.md         # ← You are here
├── setup_bacon_node.sh     # VPS setup script for Bitcoin Core + Runes node
├── wrangler.toml           # Cloudflare Worker configuration
├── public/                 # Static HTML pages & assets (auto-served by Cloudflare)
│   ├── index.html          # Main landing page
│   ├── getting-started.html
│   ├── api-reference.html
│   ├── bitcoin-integration.html
│   ├── solana-integration.html
│   ├── github-actions.html
│   ├── security.html
│   ├── styles.css
│   ├── script.js
│   └── static/images/      # Image assets
├── src/                    # Cloudflare Worker Python source
│   └── index.py            # Main request handler / router
├── ord-server/             # Bitcoin Ordinals / Runes Flask server
│   ├── .env.example        # ord-server environment variables template
│   ├── ord-api.py          # Flask API server
│   ├── ord-flask.service   # systemd service file (for VPS deployment)
│   ├── example-split.yaml  # Example batch split configuration
│   └── requirements.txt    # Python dependencies
└── tests/                  # Test suite
```

---

## Making Changes

### Branching Strategy

Always create a new branch for your work. **Never commit directly to `main`.**

```bash
# Sync with upstream first
git fetch upstream
git checkout main
git merge upstream/main

# Create your feature/fix branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-name
```

Branch naming conventions:

| Type | Pattern | Example |
|---|---|---|
| New feature | `feature/short-description` | `feature/add-solana-rewards` |
| Bug fix | `fix/short-description` | `fix/broken-redirect-route` |
| Documentation | `docs/short-description` | `docs/update-api-reference` |
| Refactor | `refactor/short-description` | `refactor/clean-worker-routes` |

### Coding Standards

- **Python:** Follow [PEP 8](https://peps.python.org/pep-0008/). Keep functions small and focused.
- **Comments/Docstrings:** All new functions should have a short docstring explaining what they do.
- **Secrets:** Never hardcode secrets or credentials. Use environment variables and Wrangler secrets.
- **Cloudflare Workers:** Remember — the Python Worker runs in Cloudflare's edge runtime. Avoid standard library functions that rely on filesystem I/O (`open()`, `os.path`, etc.) — they are not supported.

### Testing

Before pushing your changes, verify that:

1. `npm run dev` starts without errors.
2. The specific route or feature you touched behaves as expected in the browser or via `curl`.
3. Existing functionality (redirects, static assets) is not broken.

---

## Opening a Pull Request

1. **Push your branch** to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a PR** on [github.com/OWASP-BLT/BLT-Rewards](https://github.com/OWASP-BLT/BLT-Rewards) from your fork's branch to `upstream/main`.

3. **Fill out the PR template** completely:
   - Clearly describe *what* changed and *why*.
   - Link any related issue (e.g. `Closes #42`).
   - Include screenshots or `curl` output for visual/API changes.

4. **PR checklist** before requesting review:
   - [ ] My branch is up to date with `main`.
   - [ ] No secrets or credentials are committed.
   - [ ] New code has comments / docstrings where appropriate.
   - [ ] Static files in `public/` are not accidentally modified (unless that's the intent).
   - [ ] `npm run dev` runs without errors.

5. A maintainer will review your PR. Be ready to make requested changes — discussions are normal and healthy.

> **Keep PRs focused.** One PR should do one thing. If you spot other issues while working, open separate issues or PRs for them.

---

## Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/OWASP-BLT/BLT-Rewards/issues/new) and include:

- **For bugs:**
  - A clear description of the problem.
  - Steps to reproduce it.
  - What you expected vs. what actually happened.
  - Your OS, Node.js version, and Python version.
  - Any relevant error messages or logs.

- **For feature requests:**
  - The problem you're trying to solve.
  - Your proposed solution or idea.
  - Any alternatives you considered.

> **Security vulnerabilities** should **not** be reported as public issues. Please follow the guidance in [public/security.html](public/security.html) or contact the OWASP BLT team directly.

---

## Code of Conduct

This project follows the spirit of the [OWASP Code of Conduct](https://owasp.org/www-policy/operational/code-of-conduct). As a contributor, you agree to:

- **Be respectful and inclusive.** Treat everyone with kindness, regardless of their experience level, background, or identity.
- **Be constructive.** Critique ideas, not people. Offer suggestions, not just complaints.
- **Be collaborative.** Help others get unblocked. Share knowledge freely.
- **Be patient.** Maintainers are volunteers. Reviews may take time.
- **Keep it professional.** Harassment, discrimination, or offensive language of any kind will not be tolerated.

Violations can be reported to the OWASP BLT team via the [OWASP BLT repository](https://github.com/OWASP-BLT/BLT).

---

## Need Help?

- Browse the [existing issues](https://github.com/OWASP-BLT/BLT-Rewards/issues) — your question might already be answered.
- Check the [documentation pages](public/) for guides on Bitcoin integration, Solana integration, and the API reference.
- Tag a maintainer in your issue or PR if you're stuck.

We're glad you're here — happy contributing! 🥓
