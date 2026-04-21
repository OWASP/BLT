# BLT-SafeCloak

[![Video Chat E2E Tests](https://github.com/OWASP-BLT/BLT-SafeCloak/actions/workflows/test.yml/badge.svg)](https://github.com/OWASP-BLT/BLT-SafeCloak/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Node >= 18](https://img.shields.io/badge/node-%3E%3D18-339933?logo=node.js&logoColor=white)](package.json)
[![Python >= 3.11](https://img.shields.io/badge/python-%3E%3D3.11-3776AB?logo=python&logoColor=white)](pyproject.toml)

Privacy-focused real-time communication for OWASP BLT, built on Cloudflare Workers with a browser-first security model.

## Table of Contents

- [What is BLT-SafeCloak](#what-is-blt-safecloak)
- [Core Capabilities](#core-capabilities)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Milestones](#milestones)
- [Key Decisions](#key-decisions)
- [What We Won't Have (for now)](#what-we-wont-have-for-now)
- [Quick Start](#quick-start)
- [Development Commands](#development-commands)
- [Testing](#testing)
- [Deployment](#deployment)
- [Routes](#routes)
- [Repository Structure](#repository-structure)
- [Security Notes](#security-notes)
- [Contributing](#contributing)
- [License](#license)

## What is BLT-SafeCloak

BLT-SafeCloak extends the OWASP BLT ecosystem with secure collaboration primitives:

- live peer-to-peer video/voice communication,
- privacy controls and explicit consent UX,
- secure notes and privacy-first browser behavior.

The project prioritizes practical privacy and operational simplicity over heavy backend complexity.

## Core Capabilities

- **Secure video room flow** with a dedicated pre-join lobby and in-room experience.
- **Adaptive communication mode** that shifts to walkie-talkie behavior when participant count grows.
- **Voice controls** including effects and persisted user preferences between lobby and room.
- **Consent-centered UX** integrated directly into call workflows.
- **Cloudflare Worker delivery model** for low-latency global hosting.
- **Automated end-to-end validation** for critical real-time paths.

## Architecture at a Glance

- **Runtime:** Cloudflare Python Workers (`src/main.py`)
- **Frontend:** static HTML + vanilla JavaScript (`src/pages`, `public/js`)
- **Assets:** served from Worker assets (`public/`)
- **Signaling in tests:** local PeerJS server for deterministic CI/local E2E runs
- **Design direction:** browser-first privacy with minimal server-side state

## Milestones

Completed:

- ✅ **M1 — Worker foundation and clean routing** (`/`, `/video-chat`, `/video-room`, `/notes`, `/consent`)
- ✅ **M2 — Video lobby + in-room collaboration experience**
- ✅ **M3 — Voice controls, persistence, and adaptive walkie-talkie mode**
- ✅ **M4 — Stable E2E workflow in CI with local signaling and mocked media**

Current focus:

- 🔄 **Documentation and contributor onboarding hardening**
- 🔄 **Incremental privacy/UX improvements in real-time flows**

## Key Decisions

- **Separate lobby and room pages** to keep pre-join setup isolated from in-call controls.
- **Keep content close to the client**: prioritize peer-to-peer media and browser-side protection mechanisms.
- **Scale behavior by room size**: use walkie-talkie interaction when full video does not scale well.
- **Favor deterministic testing**: avoid public signaling dependencies in automated tests.
- **Use minimal backend surface area**: route and serve assets from Workers, keep business logic client-heavy.

## What We Won't Have (for now)

To preserve privacy and keep the project focused, this repository is **not currently targeting**:

- ❌ A centralized account system and full user-profile backend.
- ❌ Server-side storage of call media/content as a primary workflow.
- ❌ Heavy, stateful backend orchestration for routine room operation.
- ❌ A monolithic framework migration away from the current static-pages + Worker model.

## Quick Start

### Requirements

- Node.js **18+**
- Python **3.11+**
- Cloudflare account (for deploy)

### Install

```bash
npm install
npm run setup
```

### Run locally

```bash
npm run dev
```

App runs at `http://localhost:8787`.

## Development Commands

```bash
# format Python + frontend files
npm run format

# check formatting only
npm run format:check

# static type checks
npm run typecheck

# main quality gate
npm run check

# clean __pycache__ directories
npm run clean
```

## Testing

Full project test command:

```bash
pytest tests/ -v --tb=short
```

For video-chat E2E tests, install Playwright Chromium once:

```bash
python -m playwright install chromium --with-deps
```

CI runs the same E2E test path via `.github/workflows/test.yml`.

## Deployment

```bash
npm run deploy
```

Wrangler config is defined in `wrangler.toml`.

## Routes

- `/` — home / product overview
- `/video-chat` — pre-join lobby
- `/video-room` — secure in-call room
- `/notes` — secure notes interface
- `/consent` — consent interface

## Repository Structure

```text
src/
  main.py              # Worker entrypoint and routing
  libs/
    utils.py           # response helper utilities
  pages/               # HTML pages
public/
  css/                 # styles
  js/                  # client logic (video, voice, notes, consent, theme)
  img/                 # static images
tests/
  test_video_chat.py   # end-to-end + integration behavior checks
  test_utils.py        # backend utility and routing tests
.github/workflows/
  test.yml             # CI workflow
```

## Security Notes

- This project follows a privacy-first architecture and avoids unnecessary server-side handling of sensitive communication data.
- If you find a vulnerability, please open a private/security-focused report through the OWASP BLT project channels before public disclosure.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

Licensed under the [MIT License](LICENSE).
