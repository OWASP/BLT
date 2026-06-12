# SafeCloak

A Qt 6 desktop chat app for your local network, styled to match the
BLT-SafeCloak theme. Think Slack, but self-organizing on your LAN with no
internet dependency: channels, a member list, and TLS-encrypted traffic.

![Setup](docs/page-setup.png)
![Chat](docs/page-chat.png)

## Mesh-only chat

SafeCloak has no host/join mode. Every node announces itself over UDP
(multicast + broadcast + loopback), publishes its usable local IPv4 addresses,
dials every discovered peer immediately, and floods messages through the mesh
with duplicate suppression. Nodes appear in the member list as soon as they
are discovered, then lose the
`(discovered)` note once the encrypted peer link is live.

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

## Building

Requires Qt 6.4+ (Widgets, Network), CMake 3.16+, a C++17 compiler, and the
`openssl` CLI at runtime (used once to generate the node certificate).

```sh
cd client
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/safecloak
```

Or use the helper script: `./run.sh` builds and launches, `./run.sh clean`
clears the build cache, `./run.sh rebuild` does both, and `./run.sh test`
runs the headless tests.

### Versioning

Every desktop-client change must bump the version in `client/CMakeLists.txt`.
The version is baked into the app UI and used by Quick update, so do this even
for small UI, documentation, or networking fixes.

To install without a checkout, the website serves a one-line installer that
grabs the latest CI build (or compiles from source):

```sh
curl -fsSL https://<site>/install.sh | bash
```

### Tests

A headless smoke test covers mesh discovery, bidirectional roster visibility,
channel propagation, mesh flooding, direct messages, and cross-IP loopback
simulation (built by default). Test nodes use a private discovery tag, so
they do not appear in a running SafeCloak window on the same machine or
LAN:

```sh
QT_QPA_PLATFORM=offscreen ./build/safecloak-tests
```

## How encryption works (and its limits)

- Every mesh peer link is TLS 1.2+. Nothing is ever sent in plaintext over TCP.
- On first run each installation generates a self-signed RSA-2048
  certificate (stored under the per-user app data directory), which it
  presents on every inbound connection. Its SHA-256 fingerprint is shown in
  the chat header.
- Because certificates are self-signed, peers are **encrypted but not
  authenticated**: a machine on your LAN could impersonate a mesh node (no
  protection against an active man-in-the-middle on the local network).
  Compare fingerprints out-of-band if that matters for your threat model.
- UDP discovery announcements contain only the display name, a random node id,
  and a port — never message content.

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
- The sidebar status shows your local IPs plus the active UDP and TCP ports.
  The message pane logs discovery, dial attempts, timeouts, and socket/TLS
  errors so you can see exactly where a peer link is failing.
- When the app was built from a local checkout, the home screen shows a
  "Quick update" button that pulls the latest version, rebuilds, and
  relaunches the app.
- Every node dials every discovered peer immediately and rotates through the
  peer's advertised IP addresses when a dial times out. If both sides dial at
  once, duplicate links are resolved deterministically.
