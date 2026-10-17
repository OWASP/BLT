# Changelog

All notable changes to BLT-SafeCloak are tracked here.

Entries before `0.9.0` were backfilled from the repository history and project
documentation. The repo does not currently have historical Git tags, so older
version numbers are milestone labels rather than previously published tags.

## 0.9.0 - 2026-06-14

### Added

- Added macOS desktop-client support with a real `SafeCloak.app` bundle.
- Added a GitLab macOS arm64 CI job that builds, tests, packages, and publishes
  `client/dist/safecloak-macos-arm64.zip`.
- Added a macOS packaging helper that runs `macdeployqt`, bundles Homebrew
  OpenSSL runtime libraries, ad-hoc signs the app, and produces the zip artifact.
- Added installer auto-detection for Linux and macOS. Linux keeps using the
  existing GitLab binary artifact; macOS arm64 installs the app bundle to
  `~/Applications/SafeCloak.app` and creates a `safecloak` launcher.
- Added desktop installer/CI regression tests so the Linux and macOS artifact
  paths stay wired together.
- Added this changelog and backfilled the major project history.

### Changed

- Bumped the desktop client from `0.8.4` to `0.9.0` for the macOS release.
- Made `client/run.sh` portable across Linux and macOS, including Homebrew Qt
  and OpenSSL discovery and non-`nproc` build parallelism.
- Updated the in-app Quick update flow to pass Homebrew Qt/OpenSSL CMake hints
  on macOS and relaunch from `SafeCloak.app`.
- Updated desktop-client docs and homepage install copy to describe Linux and
  macOS installation.

## 0.8.0 - 2026-06-12

### Added

- Added the Qt 6 SafeCloak desktop LAN chat client.
- Added self-organizing LAN mesh chat with UDP discovery, TLS peer links,
  duplicate suppression, direct messages, Slack-style channels, presence,
  typing indicators, avatars, reactions, file sharing, and history sync.
- Added encrypted server-room mode backed by Cloudflare Durable Objects. The
  server relays ciphertext envelopes while the desktop client derives an
  AES-256-GCM room key from the room name and passphrase.
- Added per-installation TLS identity generation and fingerprint display.
- Added a Settings window for display name, avatar, and network diagnostics.
- Added a Linux installer that downloads the latest GitLab CI client artifact
  or builds from source.
- Added GitLab CI coverage for the desktop client build and headless backend
  smoke tests.

### Changed

- Reworked mesh networking around stable LAN ports, direct-link retries, LAN
  fallback packets, and clearer diagnostics.
- Added evidence-based firewall guidance so warnings appear only after repeated
  connectivity failures without healthy inbound traffic.
- Added author-only message edit/delete support across mesh and server chat,
  including tombstones for deleted messages.
- Improved chat scrolling so new rows are brought into readable view.
- Hardened server-room WebSocket routing and Cloudflare Worker compatibility.

## 0.7.0 - 2026-05-24

### Added

- Added complete browser test coverage for major static pages, JavaScript
  modules, routing branches, and video-chat flows.
- Added a three-client chat E2E test with disconnect handling and history replay.
- Added README milestones, reliability targets, and a prioritized roadmap for
  5-person video and larger audio rooms.

### Changed

- Stabilized walkie-talkie floor-state synchronization, including late joiners
  and stale profile updates.
- Fixed call-glare deadlocks in full-mesh group calls.
- Improved username display, walkie-talkie mic visibility, connection handling,
  and chat reliability.
- Added secure default response headers and allowlist-based CORS handling.
- Replaced consent entry ID generation with `Crypto.randomId()`.
- Consolidated shared UI escaping/capitalization helpers and fixed warning toast
  styling.
- Bumped vulnerable JavaScript dependencies.

## 0.6.0 - 2026-04-28

### Added

- Added walkie-talkie propagation so the host's selected mode reaches every
  participant on join.
- Added floor-state corrections so participants converge on the same
  push-to-talk state.
- Added resizable video-room sidebar support.

### Changed

- Restored responsive video-room layout after sidebar and room-mode changes.
- Widened glare handling until replacement calls are accepted.
- Replaced unsafe URL substring checks with set equality to satisfy CodeQL.
- Fixed the notes summarizer `indexOf` bug.

## 0.5.0 - 2026-04-21

### Added

- Added a manual light/dark theme with storage-safe prepaint initialization.
- Added a 5-participant video cap and walkie-talkie fallback controls.
- Added lobby opt-in for walkie-talkie mode and real-time floor cue UI.
- Added encrypted in-room group chat history stored per room.
- Added participant controls such as individual mute, raise-hand state, saved
  display-name badge, and room-owner indicators.

### Changed

- Hid video-only controls in walkie-talkie mode and refined push-to-talk floor
  claim/release behavior.
- Improved peer reconnection behavior and screen-share cleanup.
- Updated README roadmap around scalable audio and relay architecture options.

## 0.4.0 - 2026-04-19

### Added

- Added in-room group chat over data channels.
- Added shareable room links, URL-persistent room IDs, and invite-link handling.
- Added voice preference persistence across lobby and room.
- Added room ID copy fallback behavior and resilient clipboard cleanup.
- Added real-time raise-hand indicators and participant-count synchronization.

### Changed

- Improved voice changer algorithms for deep, robot, alien, and phone modes.
- Fixed media default states so microphone and camera can start off by default
  while still allowing first-click enablement.
- Improved call failure behavior, room ID persistence, hangup flow, and
  return-home navigation.
- Hardened worker error handling, sanitized error responses, CORS headers, and
  cancelled-task propagation.
- Improved consent validation and switched consent entry IDs to secure random
  IDs.

## 0.3.0 - 2026-04-07

### Added

- Added a separate pre-join lobby and in-room video experience.
- Added camera preview, media preferences, display names, avatars, and room copy
  affordances.
- Added real-time voice effects with effect intensity and persona controls.
- Added PeerJS-backed E2E tests that run against a local signaling server.

### Changed

- Improved video-room layout, mobile behavior, and always-visible voice controls.
- Removed brittle CDN integrity handling from the PeerJS script path.
- Fixed anchor scroll offsets and toast warning styling.

## 0.2.0 - 2026-03-21

### Added

- Added multi-participant WebRTC mesh calls.
- Added shareable room links and immediate visibility for connecting
  participants.
- Added consent template attestation validation.
- Added safer response utilities with consistent CORS handling and safer JSON
  serialization.
- Added unknown-route 404 behavior and tests.

### Changed

- Improved camera and microphone error handling, including browser-specific
  camera guidance.
- Removed inline consent log action handlers.
- Hardened request path handling to address CodeQL path-expression alerts.
- Sanitized toast rendering and shared UI text helpers.

## 0.1.0 - 2026-02-20

### Added

- Initial BLT-SafeCloak web app with landing page, secure video chat, encrypted
  notes, consent protection, and static assets.
- Added Cloudflare Workers hosting and clean route handling for `/`,
  `/video-chat`, `/video-room`, `/notes`, and `/consent`.
- Added client-side AES-GCM encryption primitives for sensitive browser data.
- Added basic project tooling for Python, Node.js, formatting, type checking,
  and browser tests.

### Changed

- Migrated the original static site from GitHub Pages toward Cloudflare Workers.
- Refactored the project structure around `src/pages`, `public`, shared
  utilities, and testable routing helpers.
