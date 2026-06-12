# SafeCloak Chat

A Qt 6 desktop chat app for your local network, styled to match the
BLT-SafeCloak theme. Think Slack, but self-hosted on your LAN with no
internet dependency: channels, a member list, and TLS-encrypted traffic.

![Setup](docs/page-setup.png)
![Chat](docs/page-chat.png)

## Modes

| Mode | What it does |
| --- | --- |
| **Host a server** | This machine runs the room. It relays messages, owns the channel list and roster. Others join with your IP and port. |
| **Join a server** | Connect to a machine running in server mode. |
| **Mesh mode** | No server at all. Nodes announce themselves over UDP (multicast + broadcast + loopback), open TLS links to every discovered peer, and flood messages through the mesh with duplicate suppression. Nodes appear in the member list as they are discovered. |

In all modes you get Slack-style channels (`#general` and `#random` by
default, "+ Add channel" creates more and propagates them to everyone) and
direct messages — click a member in the sidebar to start a one-to-one chat.
In server mode DMs are relayed only between the two parties; in mesh mode
they go over the direct TLS link when one exists and are otherwise routed
through intermediate nodes (which forward but never display them).

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

To install without a checkout, the website serves a one-line installer that
grabs the latest CI build (or compiles from source):

```sh
curl -fsSL https://<site>/install.sh | bash
```

### Tests

A headless smoke test covers the server relay, channel propagation, mesh
discovery, and mesh flooding (built by default):

```sh
QT_QPA_PLATFORM=offscreen ./build/safecloak-tests
```

## How encryption works (and its limits)

- Every connection — client→server and mesh peer links — is TLS 1.2+.
  Nothing is ever sent in plaintext over TCP.
- On first run each installation generates a self-signed RSA-2048
  certificate (stored under the per-user app data directory), which it
  presents on every inbound connection. Its SHA-256 fingerprint is shown in
  the chat header.
- Because certificates are self-signed, peers are **encrypted but not
  authenticated**: a machine on your LAN could impersonate a server or mesh
  node (no protection against an active man-in-the-middle on the local
  network). Compare fingerprints out-of-band if that matters for your
  threat model.
- UDP discovery announcements (mesh mode) contain only the display name,
  a random node id, and a port — never message content.

## Network details

- Server mode listens on the port you choose (default 47800).
- Mesh discovery uses UDP ports 45454–45463 and multicast group
  239.255.43.21; each instance on a machine takes the next free port, so up
  to 10 instances per host can participate.
- Mesh peer links use ephemeral TLS ports; the node with the smaller node id
  normally initiates. If that node can't see the other (some networks drop
  multicast or broadcast in one direction), nodes keep introducing
  themselves via direct unicast replies and the other side dials after a
  short grace period; duplicate links are resolved deterministically.
