# BLT-SafeCloak

[![Video Chat E2E Tests](https://github.com/OWASP-BLT/BLT-SafeCloak/actions/workflows/test.yml/badge.svg)](https://github.com/OWASP-BLT/BLT-SafeCloak/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Node >= 18](https://img.shields.io/badge/node-%3E%3D18-339933?logo=node.js&logoColor=white)](package.json)
[![Python >= 3.11](https://img.shields.io/badge/python-%3E%3D3.11-3776AB?logo=python&logoColor=white)](pyproject.toml)

Privacy-focused peer-to-peer communication platform built on Cloudflare Workers. Provides secure video chat, voice communication, AI-powered notes, and explicit consent management.

## Table of Contents

- [Reliability Targets](#reliability-targets)
- [Roadmap](#roadmap)
- [Open Issues — Priority Tracker](#open-issues--priority-tracker)
- [Open PRs — Merge Priority](#open-prs--merge-priority)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Development Commands](#development-commands)
- [Testing](#testing)
- [Deployment](#deployment)
- [Routes](#routes)
- [Repository Structure](#repository-structure)
- [Security Notes](#security-notes)
- [Contributing](#contributing)
- [License](#license)

---

## Reliability Targets

The primary goal is for users to rely on BLT-SafeCloak in two distinct modes:

| Mode                      | Target                                                     | Status                            |
| ------------------------- | ---------------------------------------------------------- | --------------------------------- |
| **Full Video**            | Up to **5 participants** with camera + mic + screen share  | 🔄 Stabilising (active bug fixes) |
| **Audio / Walkie-Talkie** | Up to **500 participants** with push-to-talk floor control | 🏗️ Architecture redesign required |

### Technical notes

- **5-person video** runs as a full WebRTC mesh (each peer connects to every other peer). This works well at ≤5 nodes. The participant cap (`MAX_VIDEO_PARTICIPANTS = 5`) is already enforced in `public/js/video.js`.
- **Walkie-talkie mode** activates automatically above 5 participants, disabling video and enabling push-to-talk floor control. The current mesh architecture is estimated to support roughly 20–30 practical P2P audio peers (pending benchmark validation — see Phase 3). Reaching **500** requires a relay or selective-forwarding architecture (see Phase 3 below).

---

## Roadmap

### ✅ Completed

- **M1** — Cloudflare Worker foundation with clean URL routing (`/`, `/video-chat`, `/video-room`, `/notes`, `/consent`)
- **M2** — Separate pre-join lobby and in-room experience
- **M3** — Voice effects, user preference persistence across lobby and room
- **M4** — Walkie-talkie mode (auto-activated above 5 participants) with push-to-talk floor control
- **M5** — Stable E2E test suite running in CI with local PeerJS signaling
- **M6** — Consent-centred UX: declining recording does not block joining, alerts all peers instead

---

### 🔄 Phase 1 — Reliable 5-person video (current focus)

Goal: any group of up to 5 people can start a video call from scratch without hitting a blocking bug.

**Must-fix bugs (blocking reliability):**

- [ ] **#116** Auto-join skips name prompt — joiners appear without a display name
- [ ] **#100** Refresh reconnects a disconnected participant automatically
- [ ] **#99** Screen-share makes local camera tile disappear
- [ ] **#91** Noise suppression toggle in lobby has no effect

**Priority PRs to review/merge:**

- [ ] **#123** Walkie-talkie audio constraints, peer-unavailable handling, device fallback + E2E test ← _merge first_
- [ ] **#63** Safari lobby camera/mic permission prompt not appearing
- [ ] **#46** URL join handling — invalid peer ID init
- [ ] **#38** Screen-share toggle fix
- [ ] **#92** Noise suppression fix (resolves #91)
- [ ] **#50** Toast warning style fix (resolves #111 — invisible toasts in light mode)
- [ ] **#107** Allow call join on consent decline (resolves #106)
- [ ] **#68** Validate legal checkbox in consent form (resolves #67)
- [ ] **#114** Room-owner badge and stop invite-link auto-join from lobby (resolves #116 partially)

---

### 🔜 Phase 2 — Walkie-talkie polish for mid-size rooms (20–30 participants)

Goal: a club, class, or event team can use walkie-talkie mode reliably without floor-control glitches or audio dropouts.

- [ ] Automated stress tests for walkie-talkie mode with 10+ simulated peers
- [ ] Floor-request queue — show who is waiting to speak
- [ ] Reconnect logic hardening when a floor-holder drops mid-transmission
- [ ] Audio level visualiser in walkie-talkie mode (show who is transmitting)
- [ ] Mobile push-to-talk UX (large tap target, hold-to-speak gesture)
- [ ] Merge **#101** — deafen control (auto-mutes mic, remote audio-only playback)

---

### 🔜 Phase 3 — Scalable audio relay for up to 500 participants

> ⚠️ The current full-mesh P2P model cannot scale to 500 simultaneous audio streams. Each peer would need ~499 connections. This phase requires a new architectural component.

**Architecture options under consideration:**

1. **Selective Forwarding Unit (SFU)** — e.g. mediasoup or Janus. Each client sends one stream to the SFU, which forwards it selectively. Requires a long-running server outside Cloudflare Workers (traditional VPS/container infrastructure).
2. **Audio relay over Cloudflare Durable Objects** — Durable Objects provide persistent state and long-running WebSocket connections on Cloudflare's edge, making them a candidate for a lightweight audio relay without leaving the Cloudflare platform; full SFU-grade media processing is not natively supported, so this option is best suited for signaling and floor-control relay with WebRTC media still flowing between peers at smaller scales. Feasibility TBD.
3. **Hierarchical audio mesh** — a small set of "super-peers" relay audio to sub-groups. Lower infrastructure cost but harder floor control.

**Prerequisite tasks:**

- [ ] Open an architectural design issue and gather community input on SFU vs. relay approach
- [ ] Benchmark current mesh limit (measure degradation at 10, 20, 30 nodes)
- [ ] Evaluate Cloudflare Calls API or Durable Objects as a relay layer
- [ ] Add server-side signaling to coordinate floor control at scale
- [ ] Update E2E test harness to cover relay path

---

### 🔜 Phase 4 — Community & contributor experience

- [ ] Merge **#57** / **#30** — replace npx/npm wrangler with pywrangler (resolves #32; removes Node.js toolchain dependency from the Python-centric deployment path; see issue #32 for discussion)
- [ ] Merge **#112** — comprehensive README + milestone docs
- [ ] Merge **#43** — call health panel with WebRTC stats (helps diagnose relay issues)
- [ ] Merge **#60** — PWA manifest + service worker (offline resilience)
- [ ] Merge **#36** / **#13** — sanitize caller name in consent modal (XSS fix)
- [ ] Merge **#89** — use `Crypto.randomId()` for consent entry IDs
- [ ] Merge **#49** — SRI integrity hashes for CDN assets
- [ ] Merge **#48** — consolidate duplicate `escHtml` into shared `ui.js`

---

## Open Issues — Priority Tracker

| #                                                             | Title                                                | Phase | Priority  |
| ------------------------------------------------------------- | ---------------------------------------------------- | ----- | --------- |
| [#116](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/116) | Auto-join skips name prompt                          | 1     | 🔴 High   |
| [#100](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/100) | Refresh reconnects disconnected participant          | 1     | 🔴 High   |
| [#99](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/99)   | Screen share makes local video disappear             | 1     | 🔴 High   |
| [#91](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/91)   | Noise suppression button no effect in lobby          | 1     | 🔴 High   |
| [#106](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/106) | Consent screen blocks join instead of alerting peers | 1     | 🟠 Medium |
| [#111](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/111) | Toast notifications invisible in light mode          | 1     | 🟠 Medium |
| [#67](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/67)   | Legal checkbox not validated before consent submit   | 1     | 🟠 Medium |
| [#108](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/108) | Avatar upload with real-time P2P propagation         | 4     | 🟡 Low    |
| [#32](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/32)   | Move away from npx/npm                               | 4     | 🟡 Low    |
| [#21](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/21)   | Global light/dark theme toggle                       | 4     | 🟡 Low    |
| [#19](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/19)   | Consent modal contrast failure                       | 1     | 🟠 Medium |
| [#18](https://github.com/OWASP-BLT/BLT-SafeCloak/issues/18)   | "Connect Securely" affordance improvement            | 1     | 🟡 Low    |

---

## Open PRs — Merge Priority

PRs are grouped by the phase they unblock. Review Phase 1 PRs first.

### Phase 1 — merge to stabilise 5-person video

| PR                                                                                                                    | Title                                                            | Resolves |
| --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | -------- |
| [#123](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/123)                                                           | Walkie-talkie audio constraints, error handling, device fallback | —        |
| [#114](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/114)                                                           | Room-owner badge; stop invite-link auto-join from lobby          | #116     |
| [#121](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/121)                                                           | Security headers + disable recording on consent decline          | #106     |
| [#115](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/115)                                                           | Allowlist-based CORS origin validation                           | —        |
| [#107](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/107)                                                           | Allow call join on consent decline                               | #106     |
| [#92](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/92)                                                             | Noise suppression lobby fix                                      | #91      |
| [#63](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/63)                                                             | Safari camera/mic permission prompt                              | —        |
| [#50](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/50)                                                             | Toast warning style (light-mode visibility)                      | #111     |
| [#46](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/46)                                                             | URL join handling — invalid peer init prevention                 | —        |
| [#38](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/38)                                                             | Screen-share toggle fix                                          | #99      |
| [#68](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/68)                                                             | Validate legal checkbox before consent submit                    | #67      |
| [#37](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/37)                                                             | Modal contrast and design alignment                              | #19      |
| [#36](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/36) / [#13](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/13) | Sanitize caller name in consent modal (XSS)                      | —        |

### Phase 2 — walkie-talkie polish

| PR                                                          | Title                             |
| ----------------------------------------------------------- | --------------------------------- |
| [#101](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/101) | Deafen control with mic auto-mute |
| [#122](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/122) | Resizable sidebar for video room  |

### Phase 4 — contributor experience

| PR                                                                                                                    | Title                                           |
| --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| [#112](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/112)                                                           | Comprehensive README refresh                    |
| [#57](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/57) / [#30](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/30) | Replace npx/npm wrangler with pywrangler        |
| [#60](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/60)                                                             | PWA manifest + service worker                   |
| [#56](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/56)                                                             | Room validation endpoints                       |
| [#49](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/49)                                                             | SRI integrity hashes for CDN assets             |
| [#48](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/48)                                                             | Consolidate duplicate `escHtml` into `ui.js`    |
| [#47](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/47)                                                             | Font Awesome icon classes for mic/camera toggle |
| [#45](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/45)                                                             | Fix anchor scroll offset                        |
| [#43](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/43)                                                             | Call health panel with WebRTC stats             |
| [#41](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/41)                                                             | Anti-recording noise cloak                      |
| [#31](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/31)                                                             | Increase E2E test timeout to 120 s              |
| [#28](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/28)                                                             | Emoji reactions + P2P chat                      |
| [#12](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/12)                                                             | Real-time voice-changing effects                |
| [#10](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/10)                                                             | Options to start or join an existing call       |
| [#89](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/89)                                                             | `Crypto.randomId()` for consent entry IDs       |
| [#73](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/73)                                                             | Public room creation and homepage discovery     |
| [#66](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/66)                                                             | Mirror camera                                   |
| [#61](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/61)                                                             | Store passphrase in sessionStorage              |
| [#51](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/51)                                                             | Fix license field and setup script typo         |
| [#8](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/8)                                                               | Google Meet integration button                  |
| [#7](https://github.com/OWASP-BLT/BLT-SafeCloak/pull/7)                                                               | Footer: last updated time + commit SHA          |

---

## Features

- **P2P Video/Voice Chat**: WebRTC-based communication with end-to-end encryption
- **Adaptive mode**: automatic switch to audio-only walkie-talkie when room exceeds 5 participants
- **Consent Management**: Built-in consent tracking; declining recording alerts peers rather than blocking the caller
- **Secure Notes**: AI-powered note-taking with client-side encryption
- **Edge Computing**: Deployed on Cloudflare's global network for low latency
- **Zero-Knowledge Architecture**: Server never accesses unencrypted content

## Architecture

- **Backend**: Python Workers on Cloudflare Edge
- **Frontend**: Vanilla JavaScript with WebRTC (PeerJS)
- **Signaling**: PeerJS public server (production) / local PeerJS server (CI/dev)
- **Deployment**: Cloudflare Workers with asset hosting
- **Encryption**: Client-side AES-GCM cryptography for all sensitive data

## Quick Start

### Requirements

- Node.js **18+**
- Python **3.11+**
- Cloudflare account (for deployment)

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

# main quality gate (format:check + typecheck)
npm run check

# clean __pycache__ directories
npm run clean
```

## Testing

Install Playwright once before running video-chat E2E tests:

```bash
python -m playwright install chromium --with-deps
```

Run all tests:

```bash
pytest tests/ -v --tb=short
```

CI runs the same suite via `.github/workflows/test.yml`.

## Deployment

```bash
npm run deploy
```

Wrangler config is in `wrangler.toml`.

## Routes

- `/` — home / product overview
- `/video-chat` — pre-join lobby
- `/video-room` — secure in-call room
- `/notes` — secure notes interface
- `/consent` — consent management

## Repository Structure

```text
src/
  main.py              # Worker entrypoint and routing
  libs/
    utils.py           # response helper utilities
  pages/               # HTML pages
public/
  css/                 # styles
  js/                  # client logic (video, voice, notes, consent, ui, crypto)
  img/                 # static images
tests/
  test_video_chat.py   # end-to-end + integration behaviour checks
  test_utils.py        # backend utility and routing tests
.github/workflows/
  test.yml             # CI workflow
```

## Security Notes

- All sensitive data is encrypted client-side before transmission.
- Server acts as a signaling relay only; no persistent storage of communication content.
- Consent verification is integrated into call workflows.
- If you find a vulnerability, please open a private/security-focused report through OWASP BLT project channels before public disclosure.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and resources.

## License

MIT License — see [LICENSE](LICENSE) for details.

## OWASP

This project is part of the OWASP Bug Logging Tool (BLT) initiative.
