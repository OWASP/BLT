# SafeCloak

A Qt 6 desktop chat app styled to match the BLT-SafeCloak theme. It can run
as a self-organizing LAN mesh with TLS peer links, or as an encrypted server
room relayed through Cloudflare Durable Objects.

![Setup](docs/page-setup.png)
![Chat](docs/page-chat.png)

## Chat modes

### LAN mesh

Every node announces itself over UDP
(multicast + broadcast + loopback), publishes its usable local IPv4 addresses,
dials every discovered peer immediately, and floods messages through the mesh
with duplicate suppression. Nodes appear in the member list as soon as they
are discovered, then lose the `(discovered)` note once the encrypted peer link
is live. Green member dots mean online; gray means discovered or offline.

You get Slack-style channels (`#general` and `#random` by default, "+ Add
channel" creates more and propagates them to everyone) and direct messages:
click a member in the sidebar to start a one-to-one chat. DMs go over the
direct TLS link when one exists and are otherwise routed through intermediate
nodes, which forward but never display them.
If a peer is visible but its TCP listener times out, SafeCloak keeps retrying
the direct TLS link and broadcasts fallback message packets over the LAN
discovery ports so nearby peers can still chat even when one direction cannot
receive unicast replies. It also uses a fixed shared LAN chat port, UDP 45453,
so every client has a stable place to receive names and messages.

### Encrypted server room

The home page can also join a server room with a `ws://` or `wss://` URL, a
room name, and a passphrase. The client derives an AES-256-GCM room key from
the room name and passphrase using PBKDF2-HMAC-SHA256. The Cloudflare Durable
Object only relays ciphertext envelopes; it cannot read names, messages,
files, typing state, reactions, or avatars.

### Messaging features

- **File sharing** — the 📎 button shares any file type (up to 64 MB). Images
  display inline, GIFs play animated, and other files show as a chip with a
  Save button. Files travel over the same encrypted mesh as text.
- **Reactions** — the 🙂+ under a message adds an emoji; reaction chips with
  counts appear under the message for everyone.
- **Avatars** — upload a picture in Settings; it is shared with peers and
  shown as a round avatar to the left of your name on every message.
- **History sync** — when you join, connected peers replay the shared-channel
  backlog (and its reactions), so late joiners see what they missed. The
  desktop client keeps the full in-memory backlog and chunks it for transfer.
- **Presence and typing** — peers are removed quickly on clean disconnect,
  member dots show online/offline state, and the composer shows who is typing.
- **Settings window** — the ⚙ button (top-right) holds your display name,
  avatar, and the network/diagnostic log, keeping the chat itself clean.

## Building

Requires Qt 6.4+ (Widgets, Network), CMake 3.16+, OpenSSL development headers,
a C++17 compiler, and the `openssl` CLI at runtime (used once to generate the
mesh node certificate).

On Debian/Ubuntu:

```sh
sudo apt install build-essential cmake git qt6-base-dev libssl-dev libxkbcommon-dev libxkbcommon-x11-dev openssl
```

```sh
cd client
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/safecloak
```

On macOS with Homebrew:

```sh
brew install cmake qt openssl@3
```

```sh
cd client
cmake -B build -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$(brew --prefix qt)" \
  -DOPENSSL_ROOT_DIR="$(brew --prefix openssl@3)"
cmake --build build --parallel "$(sysctl -n hw.logicalcpu)"
open build/SafeCloak.app
```

Or use the helper script: `./run.sh` builds and launches, `./run.sh clean`
clears the build cache, `./run.sh rebuild` does both, and `./run.sh test`
runs the headless tests. On macOS it automatically uses Homebrew's Qt and
OpenSSL prefixes when available.

### Versioning

Every desktop-client change must bump the version in `client/CMakeLists.txt`.
The version is baked into the app UI and used by Quick update, so do this even
for small UI, documentation, or networking fixes.

To install without a checkout, the website serves a one-line installer that
auto-detects Linux or macOS, grabs the latest matching CI build when available,
or compiles from source:

```sh
curl -fsSL https://<site>/install.sh | bash
```

### Tests

A headless smoke test covers room crypto, mesh discovery, bidirectional roster
visibility, online dots, clean disconnect removal, typing indicators, channel
propagation, direct messages, file transfer, reactions, avatars, history sync,
same-name users, and cross-IP loopback simulation (built by default). Test
nodes use a private discovery tag, so they do not appear in a running
SafeCloak window on the same machine or LAN:

```sh
QT_QPA_PLATFORM=offscreen ./build/safecloak-tests
```

## How encryption works (and its limits)

- Every mesh peer link is TLS 1.2+. Nothing is ever sent in plaintext over TCP.
- On first run each installation generates a self-signed RSA-2048
  certificate (stored under the per-user app data directory), which it
  presents on every inbound connection. Its SHA-256 fingerprint is logged in
  Settings.
- Because certificates are self-signed, peers are **encrypted but not
  authenticated**: a machine on your LAN could impersonate a mesh node (no
  protection against an active man-in-the-middle on the local network).
  Compare fingerprints out-of-band if that matters for your threat model.
- UDP discovery announcements contain only the display name, a random node id,
  and a port — never message content.
- Server-room traffic is encrypted before leaving the desktop client. The
  Durable Object relay only sees ciphertext envelopes and may briefly retain
  undelivered ciphertext for reconnect/offline delivery.
- Incoming names, text, filenames, MIME labels, avatars, file payloads, and
  WebSocket/frame sizes are bounded before display or decode. Message text and
  filenames are HTML-escaped in the UI, file-save suggestions are reduced to a
  basename, and oversized payloads are dropped instead of rendered.
- Server rooms reject invalid room names, oversized ciphertext, and rooms over
  the connection cap. This is still defense-in-depth, not a mathematical
  guarantee that hostile clients can never cause load; deploy rate limits and
  Cloudflare abuse controls should remain enabled.

## Troubleshooting: peers see each other but never connect

By far the most common cause is a **host firewall dropping inbound traffic.**
The symptom is exactly: one computer shows the other as a member and logs
"Discovered … / Dialing … / Direct TLS link timed out", while the other
computer doesn't see the first at all. That happens when the second computer's
firewall blocks inbound — its outbound announcements still get out (so it's
visible), but nothing can reach it back.

SafeCloak detects an active firewall at startup and shows an **"Allow through
firewall"** button in a banner above the chat. Clicking it runs the right
command via `pkexec` (a graphical password prompt) — no terminal needed. Do
this **on every computer**.

To do it by hand instead (note: `ufw` ranges use a **colon**, `firewalld`
uses a **hyphen** — using the wrong one gives ufw's `ERROR: Bad port`):

```sh
# ufw (Debian/Ubuntu)
sudo ufw allow 45453:45463/udp && sudo ufw allow 45464:45473/tcp

# firewalld (Fedora/RHEL)
sudo firewall-cmd --permanent --add-port=45453-45463/udp --add-port=45464-45473/tcp
sudo firewall-cmd --reload
```

No application-level trick can get through a firewall that drops inbound
packets, so opening these ports is required for the mesh to link up. The ports
open immediately — no app restart needed; discovery recovers within seconds.

## Network details

- Mesh discovery uses UDP ports 45454–45463 and multicast group
  239.255.43.21; each instance on a machine takes the next free port, so up
  to 10 instances per host can participate. Announcements go out on every
  network interface (multicast + each interface's directed broadcast), so
  machines with docker bridges or VPNs still discover peers on the LAN.
- LAN chat fallback uses UDP 45453 with shared binding so all clients know
  where to send and receive message packets.
- Mesh TLS listeners prefer TCP ports 45464–45473 (falling back to an
  ephemeral port). If peers see each other as "(discovered)" but never
  connect, allow TCP 45464–45473 and UDP 45453–45463 through your firewall.
- The sidebar shows only a short reachable count. Settings logs local IPs,
  active UDP/LAN/TCP ports, TLS fingerprints, discovery, dial attempts,
  timeouts, socket/TLS errors, and server send/receive activity so you can see
  exactly where a peer link is failing.
- When the app was built from a local checkout, the home screen shows a
  "Quick update" button that pulls the latest version, rebuilds, and
  relaunches the app.
- Every node dials every discovered peer immediately and rotates through the
  peer's advertised IP addresses when a dial times out. If both sides dial at
  once, duplicate links are resolved deterministically.
