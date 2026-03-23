"""
E2E test: three browser clients join the same video-chat room and each
client must see the other two participants' camera streams.

How it works
------------
1. A lightweight Python HTTP server is started locally to serve the app
   pages (src/pages/) and static assets (public/).
2. A local PeerJS signaling server (``peer`` npm package CLI) is started
   so the test does not rely on the external 0.peerjs.com cloud service.
3. The test server patches the served video-chat HTML to inject a thin
   ``window.__PEERJS_CONFIG__`` override that redirects the signaling
   client to ``ws://127.0.0.1:<peerjs_port>`` instead of 0.peerjs.com,
   and replaces the CDN peerjs.min.js script tag with a locally-served
   copy sourced from the installed ``peerjs`` npm package.
4. A single Chromium browser is launched in headless mode; each browser
   context injects a ``getUserMedia`` shim so that no physical camera or
   microphone hardware is required (a canvas-based video track and an
   AudioContext oscillator audio track are returned instead).
5. Three isolated browser contexts are created and each opens the
   video-chat page.
6. Client 2 connects to Client 1.  Both consent dialogs are accepted.
7. Client 3 connects to Client 1.  Client 3's consent dialog is accepted.
   The full-mesh data channel then automatically bridges Client 3 to
   Client 2 (no extra consent needed as both already consented).
8. The test waits for each remote <video> to have a live srcObject and
   then asserts the condition, avoiding any race between wrapper creation
   and stream attachment.

Local development setup
-----------------------
Install all dependencies::

    npm install
    pip install -r requirements-dev.txt
    playwright install chromium --with-deps

Then run the tests::

    pytest tests/ -v
"""

import http.server
import re
import socket
import socketserver
import subprocess
import threading
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent

# Path to peerjs.min.js bundled with the ``peerjs`` npm package (installed
# via ``npm install``).  Avoids any CDN dependency during tests.
_PEERJS_MIN_JS = ROOT / "node_modules" / "peerjs" / "dist" / "peerjs.min.js"

# Path to the local PeerJS signaling-server binary (``peer`` npm package).
_PEERJS_BIN = ROOT / "node_modules" / ".bin" / "peerjs"

# Seconds to wait for the local PeerJS server to become ready.
_PEERJS_STARTUP_TIMEOUT = 15

# Map clean URL paths to HTML source files.
_PAGES = {
    "/": "src/pages/index.html",
    "/video-chat": "src/pages/video-chat.html",
    "/notes": "src/pages/notes.html",
    "/consent": "src/pages/consent.html",
}

# MIME types for static asset extensions.
_MIME = {
    ".js": "application/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

# Generous timeout for WebRTC operations (all local after patching).
TIMEOUT_MS = 120_000

# Chromium flags needed for headless CI operation.
_BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
]

# JavaScript shim injected into every browser context via add_init_script.
# Falls back to a canvas + AudioContext fake stream when getUserMedia is
# unavailable (e.g. Chrome Headless Shell without an audio subsystem).
_MOCK_GET_USER_MEDIA = """
(function () {
  var _orig =
    navigator.mediaDevices && navigator.mediaDevices.getUserMedia
      ? navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices)
      : null;

  async function _fakeStream(constraints) {
    var stream = new MediaStream();
    if (!constraints || constraints.video !== false) {
      try {
        var canvas = document.createElement("canvas");
        canvas.width = 320;
        canvas.height = 240;
        canvas.getContext("2d").fillRect(0, 0, 320, 240);
        canvas
          .captureStream(10)
          .getVideoTracks()
          .forEach(function (t) {
            stream.addTrack(t);
          });
      } catch (e) {
        /* canvas stream unavailable – skip video track */
      }
    }
    if (!constraints || constraints.audio !== false) {
      try {
        var ac = new AudioContext();
        var osc = ac.createOscillator();
        var dest = ac.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        dest.stream.getAudioTracks().forEach(function (t) {
          stream.addTrack(t);
        });
      } catch (e) {
        /* AudioContext unavailable – skip audio track */
      }
    }
    return stream;
  }

  if (navigator.mediaDevices) {
    navigator.mediaDevices.getUserMedia = async function (constraints) {
      if (_orig) {
        try {
          return await _orig(constraints);
        } catch (e) {
          /* ignore – fall through to fake stream */
        }
      }
      return _fakeStream(constraints);
    };
  }
})();
"""

# Regex that matches the peerjs CDN <script> tag (spans multiple lines).
_PEERJS_SCRIPT_RE = re.compile(
    r'<script\b[^>]*\bsrc="https://unpkg\.com/peerjs[^"]*"[^>]*>.*?</script>',
    re.DOTALL,
)


def _free_port() -> int:
    """Return an unused TCP port on localhost."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _AppHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP handler that serves app pages and public assets.

    Two class-level attributes are populated by the ``base_url`` fixture
    before the server starts:

    * ``peerjs_port`` – port of the local PeerJS signaling server
    * ``peerjs_js``   – bytes of peerjs.min.js (served at /peerjs.min.js)
    """

    peerjs_port: int = 0
    peerjs_js: bytes = b""

    def do_GET(self):  # noqa: N802  (required by BaseHTTPRequestHandler interface)
        path = self.path.split("?")[0]

        # Serve the locally installed peerjs.min.js.
        if path == "/peerjs.min.js":
            self._respond(200, "application/javascript", self.__class__.peerjs_js)
            return

        # Serve HTML pages (video-chat is patched to use local signaling).
        if path in _PAGES:
            data = (ROOT / _PAGES[path]).read_bytes()
            if path == "/video-chat":
                data = _patch_video_chat_html(data, self.__class__.peerjs_port)
            self._respond(200, "text/html; charset=utf-8", data)
            return

        # Serve static files from public/.
        public_root = (ROOT / "public").resolve()
        # Sanitize the request path before any filesystem operation: strip
        # empty segments and reject any "." or ".." traversal components so
        # CodeQL can confirm that user-supplied data never flows into a path
        # expression unguarded.
        safe_parts = [p for p in path.split("/") if p and p not in (".", "..")]
        candidate = (public_root / "/".join(safe_parts)).resolve()
        # Defense-in-depth: confirm the resolved path is still within public_root.
        try:
            candidate.relative_to(public_root)
        except ValueError:
            self._respond(404, "text/plain", b"Not found")
            return
        if candidate.is_file():
            data = candidate.read_bytes()
            ct = _MIME.get(candidate.suffix, "application/octet-stream")
            self._respond(200, ct, data)
            return

        self._respond(404, "text/plain", b"Not found")

    def _respond(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        """Suppress per-request log output to keep test output clean."""



def _patch_video_chat_html(data: bytes, peerjs_port: int) -> bytes:
    """Rewrite video-chat HTML to use the local PeerJS signaling server.

    Replaces the unpkg.com CDN script tag with a local ``/peerjs.min.js``
    reference, then injects a ``window.__PEERJS_CONFIG__`` block that
    overrides the signaling-server host/port in ``video.js`` at runtime.
    """
    config_script = (
        '<script src="/peerjs.min.js"></script>\n'
        "    <script>\n"
        f"    window.__PEERJS_CONFIG__ = "
        f"{{host:'127.0.0.1',port:{peerjs_port},secure:false,path:'/',key:'peerjs'}};\n"
        "    </script>"
    )
    html = data.decode("utf-8")
    html = _PEERJS_SCRIPT_RE.sub(config_script, html)
    return html.encode("utf-8")


@pytest.fixture(scope="module")
def peerjs_server():
    """Start a local PeerJS signaling server and yield its port number.

    Uses the ``peerjs`` CLI provided by the ``peer`` npm package installed
    in ``node_modules``.  Falls back to a globally installed ``peerjs``
    binary if the local one is not present (e.g. ``npm install -g peer``).
    """
    port = _free_port()

    # Prefer the locally installed binary to avoid PATH ambiguity in CI.
    bin_path = str(_PEERJS_BIN) if _PEERJS_BIN.exists() else "peerjs"

    proc = subprocess.Popen(
        [bin_path, "--port", str(port), "--path", "/"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Wait until the TCP port is open (the server is ready to accept
    # connections) rather than relying on an HTTP status code.
    deadline = time.monotonic() + _PEERJS_STARTUP_TIMEOUT
    ready = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stdout_text = (
                proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            )
            raise RuntimeError(
                f"PeerJS server exited early (code {proc.returncode}).\n{stdout_text}"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                ready = True
                break
        except OSError:
            time.sleep(0.25)

    if not ready:
        proc.terminate()
        raise RuntimeError(
            f"Local PeerJS server did not start within {_PEERJS_STARTUP_TIMEOUT}s "
            f"on port {port}."
        )

    try:
        yield port
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="module")
def base_url(peerjs_server):
    """Start a local HTTP server and return its base URL."""
    if not _PEERJS_MIN_JS.exists():
        raise FileNotFoundError(
            f"peerjs.min.js not found at {_PEERJS_MIN_JS}. "
            "Run 'npm install' first."
        )
    _AppHandler.peerjs_js = _PEERJS_MIN_JS.read_bytes()
    _AppHandler.peerjs_port = peerjs_server
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _AppHandler)
    server.allow_reuse_address = True
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _new_context(browser):
    """Create a browser context with the getUserMedia shim pre-loaded."""
    ctx = browser.new_context(permissions=["camera", "microphone"])
    ctx.add_init_script(_MOCK_GET_USER_MEDIA)
    return ctx


def _peer_id(page) -> str:
    """Block until the peer ID has been assigned and return it."""
    page.wait_for_function(
        "document.getElementById('my-peer-id') && "
        "document.getElementById('my-peer-id').textContent.trim() !== '' && "
        "document.getElementById('my-peer-id').textContent.trim() !== 'Connecting...'",
        timeout=TIMEOUT_MS,
    )
    return page.evaluate("document.getElementById('my-peer-id').textContent.trim()")


def _accept_consent(page, timeout: int = TIMEOUT_MS):
    """Wait for the consent dialog to appear and click 'I Consent'."""
    page.wait_for_selector("#consent-allow", timeout=timeout)
    page.click("#consent-allow")


_STREAM_CHECK_JS = """
() => {
    const wrappers = Array.from(document.querySelectorAll('.video-wrapper'));
    const remotes = wrappers.slice(1);   // skip the local tile
    return (
        remotes.length === 2 &&
        remotes.every(w => {
            const v = w.querySelector('video');
            return v !== null && v.srcObject !== null;
        })
    );
}
"""


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_three_clients_connect_and_see_cameras(base_url):
    """
    Three clients join the same room.  Assert each client can see the
    other two participants' camera streams (srcObject != null).
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=_BROWSER_ARGS)
        try:
            ctx1 = _new_context(browser)
            ctx2 = _new_context(browser)
            ctx3 = _new_context(browser)

            p1 = ctx1.new_page()
            p2 = ctx2.new_page()
            p3 = ctx3.new_page()

            video_url = f"{base_url}/video-chat"
            for page in (p1, p2, p3):
                page.goto(video_url)

            # ── Collect peer IDs ─────────────────────────────────────────────
            id1 = _peer_id(p1)
            id2 = _peer_id(p2)
            id3 = _peer_id(p3)
            assert id1 and id2 and id3, "All clients must receive a peer ID"
            assert len({id1, id2, id3}) == 3, "All peer IDs must be unique"

            # ── Step 1: Client 2 calls Client 1 ─────────────────────────────
            # callPeer shows a consent dialog on the *caller* before dialling.
            p2.fill("#remote-id", id1)
            p2.click("#btn-call")
            _accept_consent(p2)  # p2 consents (caller side)
            _accept_consent(p1)  # p1 consents (callee side)

            # Wait for the p1–p2 connection to be fully established.
            p1.wait_for_function(
                "document.querySelectorAll('.video-wrapper').length >= 2",
                timeout=TIMEOUT_MS,
            )
            p2.wait_for_function(
                "document.querySelectorAll('.video-wrapper').length >= 2",
                timeout=TIMEOUT_MS,
            )

            # ── Step 2: Client 3 calls Client 1 ─────────────────────────────
            # After this call is answered, Client 1 sends Client 3 the
            # existing peer list [id2] via the data channel, and Client 3
            # automatically calls Client 2 to complete the full mesh.
            # (Both p1 and p2 already have consentGiven=true at this point.)
            p3.fill("#remote-id", id1)
            p3.click("#btn-call")
            _accept_consent(p3)  # p3 consents (caller side)
            # p1 already has consentGiven=true → no dialog

            # ── Step 3: Wait for full mesh ───────────────────────────────────
            # Every client should have 3 video wrappers: 1 local + 2 remote.
            for page in (p1, p2, p3):
                page.wait_for_function(
                    "document.querySelectorAll('.video-wrapper').length >= 3",
                    timeout=TIMEOUT_MS,
                )

            # ── Step 4: Wait for and verify live camera streams ──────────────
            # ``handleCallStream`` creates the wrapper before stream arrives, so
            # we must wait (not just assert) to avoid a race with srcObject
            # assignment.
            for page, name in ((p1, "Client 1"), (p2, "Client 2"), (p3, "Client 3")):
                page.wait_for_function(_STREAM_CHECK_JS, timeout=TIMEOUT_MS)
                assert page.evaluate(_STREAM_CHECK_JS), (
                    f"{name} should see live streams from both other participants"
                )
        finally:
            browser.close()
