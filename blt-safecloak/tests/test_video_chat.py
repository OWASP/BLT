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
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent

# Path to peerjs.min.js bundled with the ``peerjs`` npm package (installed
# via ``npm install``).  Avoids any CDN dependency during tests.
_PEERJS_MIN_JS = ROOT / "node_modules" / "peerjs" / "dist" / "peerjs.min.js"

# Seconds to wait for the local PeerJS server to become ready.
_PEERJS_STARTUP_TIMEOUT = 15

# Map clean URL paths to HTML source files.
_PAGES = {
    "/": "src/pages/index.html",
    "/video-chat": "src/pages/video-chat.html",
    "/video-room": "src/pages/video-room.html",
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

# Pre-enumerate every static file under public/ at module-load time.
# URL paths (e.g. "/js/video.js") map to their absolute Path objects.
# User-provided request paths are used only as dict keys – they never
# reach any filesystem operation directly, eliminating the CodeQL
# "Uncontrolled data used in path expression" taint entirely.
_PUBLIC_FILES: dict[str, Path] = {
    "/" + f.relative_to(ROOT / "public").as_posix(): f
    for f in (ROOT / "public").rglob("*")
    if f.is_file()
}

# Regex that matches the peerjs CDN <script> tag (spans multiple lines).
_PEERJS_SCRIPT_RE = re.compile(
    r'<script\b[^>]*\bsrc="https://unpkg\.com/peerjs[^"]*"[^>]*>.*?</script>',
    re.DOTALL,
)

# External CDN resources that are stripped from video-chat HTML at test-serve
# time so the E2E test does not hang on blocked / slow external network calls.
# Tailwind CDN <script> tag (the inline ``tailwind.config`` block that
# immediately follows it is also removed since it references ``tailwind.*``).
_TAILWIND_SCRIPT_RE = re.compile(
    r'<script\b[^>]*\bsrc="https://cdn\.tailwindcss\.com[^"]*"[^>]*>\s*</script>',
    re.DOTALL,
)
_TAILWIND_CONFIG_RE = re.compile(
    r'<script>\s*tailwind\.config\s*=\s*\{.*?\};\s*</script>',
    re.DOTALL,
)
# Google Fonts <link> tags (preconnect + stylesheet).
_GOOGLE_FONTS_RE = re.compile(
    r'<link\b[^>]*\bhref="https://fonts\.(googleapis|gstatic)\.com[^"]*"[^>]*/?>',
    re.DOTALL,
)
# Font Awesome stylesheet from cdnjs.
_FONT_AWESOME_RE = re.compile(
    r'<link\b[^>]*\bhref="https://cdnjs\.cloudflare\.com[^"]*"[^>]*/?>',
    re.DOTALL,
)


def _free_port() -> int:
    """Return an unused TCP port on localhost."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _resolve_peerjs_bin() -> list:
    """Return the argv prefix for running the PeerJS signaling-server CLI.

    Resolution order (cross-platform):
    1. ``node_modules/.bin/peerjs.cmd``  – Windows npm-installed wrapper
    2. ``node_modules/.bin/peerjs``      – Unix npm-installed binary
    3. ``shutil.which('peerjs')``        – global install on PATH
    4. ``['npx', '--yes', 'peerjs']``  – last-resort: delegate to npx
    """
    local_bin = ROOT / "node_modules" / ".bin" / "peerjs"
    if sys.platform == "win32":
        cmd_wrapper = local_bin.with_suffix(".cmd")
        if cmd_wrapper.exists():
            return [str(cmd_wrapper)]
    if local_bin.exists():
        return [str(local_bin)]
    found = shutil.which("peerjs")
    if found:
        return [found]
    return ["npx", "--yes", "peerjs"]


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    """ThreadingTCPServer with SO_REUSEADDR set before the socket is bound.

    ``socketserver.ThreadingTCPServer`` only honours ``allow_reuse_address``
    if it is already True when ``server_bind`` is called (inside ``__init__``),
    so we set it as a class attribute rather than as an instance attribute after
    construction.
    """

    allow_reuse_address = True


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

        # Serve HTML pages (video-room is patched to use local signaling).
        if path in _PAGES:
            data = (ROOT / _PAGES[path]).read_bytes()
            if path == "/video-room":
                data = _patch_video_chat_html(data, self.__class__.peerjs_port)
            self._respond(200, "text/html; charset=utf-8", data)
            return

        # Serve static files from public/.
        # Look up the URL path in the pre-enumerated allowlist; user input
        # is used only as a dict key and never flows into any filesystem call.
        file_path = _PUBLIC_FILES.get(path)
        if file_path is not None:
            data = file_path.read_bytes()
            ct = _MIME.get(file_path.suffix, "application/octet-stream")
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

    1. Strips blocking external CDN resources (Tailwind, Google Fonts, Font
       Awesome) so the test does not depend on external network access.
    2. Replaces the unpkg.com CDN script tag with a local ``/peerjs.min.js``
       reference, then injects a ``window.__PEERJS_CONFIG__`` block that
       overrides the signaling-server host/port in ``video.js`` at runtime.

    Raises ``RuntimeError`` if the PeerJS script tag is not found exactly once,
    which would indicate the HTML template has changed in a breaking way.
    """
    config_script = (
        '<script src="/peerjs.min.js"></script>\n'
        "    <script>\n"
        f"    window.__PEERJS_CONFIG__ = "
        f"{{host:'127.0.0.1',port:{peerjs_port},secure:false,path:'/',key:'peerjs'}};\n"
        "    </script>"
    )
    html = data.decode("utf-8")

    # Strip external CDN resources that can block / slow the test.
    html = _TAILWIND_SCRIPT_RE.sub("", html)
    html = _TAILWIND_CONFIG_RE.sub("", html)
    html = _GOOGLE_FONTS_RE.sub("", html)
    html = _FONT_AWESOME_RE.sub("", html)

    # Replace PeerJS CDN tag, asserting exactly one replacement.
    html, n_subs = _PEERJS_SCRIPT_RE.subn(config_script, html)
    if n_subs != 1:
        raise RuntimeError(
            f"Expected to replace exactly one PeerJS <script> tag but found {n_subs}. "
            "The video-chat HTML template may have changed – update _PEERJS_SCRIPT_RE."
        )

    return html.encode("utf-8")


@pytest.fixture(scope="module")
def peerjs_server():
    """Start a local PeerJS signaling server and yield its port number.

    Uses the ``peerjs`` CLI provided by the ``peer`` npm package installed
    in ``node_modules``.  Falls back to a globally installed ``peerjs``
    binary or ``npx peerjs`` if the local one is not present.
    """
    port = _free_port()
    cmd = _resolve_peerjs_bin() + ["--port", str(port), "--path", "/"]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait until the TCP port is open (the server is ready to accept
    # connections) rather than relying on an HTTP status code.
    deadline = time.monotonic() + _PEERJS_STARTUP_TIMEOUT
    ready = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"PeerJS server exited early (code {proc.returncode}). "
                f"Command: {cmd}"
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
    server = _ThreadingTCPServer(("127.0.0.1", 0), _AppHandler)
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

            video_url = f"{base_url}/video-room"
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


# ---------------------------------------------------------------------------
# VoiceChanger unit tests (run in a headless browser page)
# ---------------------------------------------------------------------------

# JavaScript that exercises VoiceChanger in the browser context.
_VOICE_CHANGER_MODES_JS = """
() => {
    /* VoiceChanger must be defined */
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};

    const modes = VoiceChanger.getModes();
    const expected = ['normal', 'deep', 'chipmunk', 'robot', 'echo', 'voice1', 'voice2', 'voice3'];
    for (const m of expected) {
        if (!modes[m]) return {ok: false, error: 'Missing mode: ' + m};
        if (!modes[m].label) return {ok: false, error: 'Missing label for: ' + m};
        if (!modes[m].icon) return {ok: false, error: 'Missing icon for: ' + m};
    }
    return {ok: true};
}
"""

_VOICE_CHANGER_INIT_JS = """
async () => {
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};

    /* Build a minimal fake audio stream via AudioContext */
    let stream;
    try {
        const ac = new AudioContext();
        const osc = ac.createOscillator();
        const dest = ac.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        stream = dest.stream;
    } catch (e) {
        return {ok: false, error: 'AudioContext unavailable: ' + e.message};
    }

    const processed = VoiceChanger.init(stream);
    if (!processed) return {ok: false, error: 'init() returned falsy'};

    /* Processed stream should have at least one audio track */
    const audioTracks = processed.getAudioTracks ? processed.getAudioTracks() : [];
    if (audioTracks.length === 0) return {ok: false, error: 'No audio tracks in processed stream'};

    /* Default mode should still be normal */
    if (VoiceChanger.getMode() !== 'normal') return {ok: false, error: 'Default mode is not normal'};

    VoiceChanger.destroy();
    return {ok: true};
}
"""

_VOICE_CHANGER_SET_MODE_JS = """
async () => {
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};

    /* Build a fake stream */
    let stream;
    try {
        const ac = new AudioContext();
        const osc = ac.createOscillator();
        const dest = ac.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        stream = dest.stream;
    } catch (e) {
        return {ok: false, error: 'AudioContext unavailable: ' + e.message};
    }

    VoiceChanger.init(stream);

    const modes = ['normal', 'deep', 'chipmunk', 'robot', 'echo', 'voice1', 'voice2', 'voice3'];
    for (const mode of modes) {
        VoiceChanger.setMode(mode);
        if (VoiceChanger.getMode() !== mode) {
            VoiceChanger.destroy();
            return {ok: false, error: 'setMode(' + mode + ') did not update getMode()'};
        }
        /* getProcessedStream() must remain valid after a mode switch */
        const ps = VoiceChanger.getProcessedStream();
        if (!ps) {
            VoiceChanger.destroy();
            return {ok: false, error: 'getProcessedStream() returned null after setMode(' + mode + ')'};
        }
    }

    VoiceChanger.destroy();
    /* After destroy, getMode resets to normal */
    if (VoiceChanger.getMode() !== 'normal') return {ok: false, error: 'getMode() after destroy() is not normal'};
    return {ok: true};
}
"""

_VOICE_CHANGER_IGNORE_UNKNOWN_MODE_JS = """
() => {
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};
    /* setMode with an unknown key must be a no-op */
    const before = VoiceChanger.getMode();
    VoiceChanger.setMode('__unknown__');
    const after = VoiceChanger.getMode();
    if (before !== after) return {ok: false, error: 'setMode(unknown) changed mode to: ' + after};
    return {ok: true};
}
"""


@pytest.fixture(scope="module")
def voice_changer_page(base_url):
    """Open a single in-call page for VoiceChanger unit tests."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=_BROWSER_ARGS)
        try:
            ctx = _new_context(browser)
            page = ctx.new_page()
            page.goto(f"{base_url}/video-room")
            # Wait for VoiceChanger to be defined (scripts loaded)
            page.wait_for_function("typeof VoiceChanger !== 'undefined'", timeout=TIMEOUT_MS)
            yield page
        finally:
            browser.close()


def test_voice_changer_modes_defined(voice_changer_page):
    """VoiceChanger.getModes() must expose all five required effect keys."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_MODES_JS)
    assert result["ok"], result.get("error", "unknown error")


def test_voice_changer_init_returns_processed_stream(voice_changer_page):
    """VoiceChanger.init() must return a MediaStream with at least one audio track."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_INIT_JS)
    assert result["ok"], result.get("error", "unknown error")


def test_voice_changer_set_mode_cycles_all_effects(voice_changer_page):
    """setMode() must switch the active mode and keep getProcessedStream() valid."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_SET_MODE_JS)
    assert result["ok"], result.get("error", "unknown error")


def test_voice_changer_ignores_unknown_mode(voice_changer_page):
    """setMode() with an unrecognised key must not change the current mode."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_IGNORE_UNKNOWN_MODE_JS)
    assert result["ok"], result.get("error", "unknown error")


# ---------------------------------------------------------------------------
# VoiceChanger monitor / mic-gain tests
# ---------------------------------------------------------------------------

_VOICE_CHANGER_MONITOR_JS = """
async () => {
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};

    /* Build a fake stream */
    let stream;
    try {
        const ac = new AudioContext();
        const osc = ac.createOscillator();
        const dest = ac.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        stream = dest.stream;
    } catch (e) {
        return {ok: false, error: 'AudioContext unavailable: ' + e.message};
    }

    VoiceChanger.init(stream);

    /* Monitor must start disabled */
    if (VoiceChanger.getMonitorEnabled()) {
        VoiceChanger.destroy();
        return {ok: false, error: 'monitor should be disabled after init'};
    }

    /* Toggle on */
    const enabled = VoiceChanger.toggleMonitor();
    if (!enabled) {
        VoiceChanger.destroy();
        return {ok: false, error: 'toggleMonitor() should return true after first toggle'};
    }
    if (!VoiceChanger.getMonitorEnabled()) {
        VoiceChanger.destroy();
        return {ok: false, error: 'getMonitorEnabled() should be true after toggle'};
    }

    /* Toggle off */
    VoiceChanger.toggleMonitor();
    if (VoiceChanger.getMonitorEnabled()) {
        VoiceChanger.destroy();
        return {ok: false, error: 'getMonitorEnabled() should be false after second toggle'};
    }

    VoiceChanger.destroy();
    return {ok: true};
}
"""

_VOICE_CHANGER_VOLUME_GAIN_JS = """
async () => {
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};

    /* Build a fake stream */
    let stream;
    try {
        const ac = new AudioContext();
        const osc = ac.createOscillator();
        const dest = ac.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        stream = dest.stream;
    } catch (e) {
        return {ok: false, error: 'AudioContext unavailable: ' + e.message};
    }

    VoiceChanger.init(stream);

    /* setMonitorVolume clamps to [0, 1] */
    VoiceChanger.setMonitorVolume(0.75);
    if (Math.abs(VoiceChanger.getMonitorVolume() - 0.75) > 0.001) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setMonitorVolume(0.75) not stored correctly'};
    }
    VoiceChanger.setMonitorVolume(5); /* above max */
    if (VoiceChanger.getMonitorVolume() !== 1) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setMonitorVolume(5) should clamp to 1, got ' + VoiceChanger.getMonitorVolume()};
    }
    VoiceChanger.setMonitorVolume(-1); /* below min */
    if (VoiceChanger.getMonitorVolume() !== 0) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setMonitorVolume(-1) should clamp to 0, got ' + VoiceChanger.getMonitorVolume()};
    }

    /* setMicGain clamps to [0, 2] */
    VoiceChanger.setMicGain(1.5);
    if (Math.abs(VoiceChanger.getMicGain() - 1.5) > 0.001) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setMicGain(1.5) not stored correctly'};
    }
    VoiceChanger.setMicGain(10); /* above max */
    if (VoiceChanger.getMicGain() !== 2) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setMicGain(10) should clamp to 2, got ' + VoiceChanger.getMicGain()};
    }
    VoiceChanger.setMicGain(-1); /* below min */
    if (VoiceChanger.getMicGain() !== 0) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setMicGain(-1) should clamp to 0, got ' + VoiceChanger.getMicGain()};
    }

    VoiceChanger.destroy();
    return {ok: true};
}
"""

_VOICE_CHANGER_INIT_IDEMPOTENT_JS = """
async () => {
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};

    function makeStream() {
        const ac = new AudioContext();
        const osc = ac.createOscillator();
        const dest = ac.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        return dest.stream;
    }

    /* Call init twice — the second call must not throw and must return a valid stream */
    try {
        const s1 = VoiceChanger.init(makeStream());
        if (!s1) return {ok: false, error: 'First init() returned falsy'};

        const s2 = VoiceChanger.init(makeStream());
        if (!s2) return {ok: false, error: 'Second init() returned falsy'};

        const tracks = s2.getAudioTracks ? s2.getAudioTracks() : [];
        if (tracks.length === 0) return {ok: false, error: 'Second init() stream has no audio tracks'};
    } catch (e) {
        VoiceChanger.destroy();
        return {ok: false, error: 'init() threw on second call: ' + e.message};
    }

    VoiceChanger.destroy();
    return {ok: true};
}
"""

_VOICE_CHANGER_INTENSITY_JS = """
async () => {
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};
    if (typeof VoiceChanger.setEffectIntensity !== 'function')
        return {ok: false, error: 'setEffectIntensity not defined'};
    if (typeof VoiceChanger.getEffectIntensity !== 'function')
        return {ok: false, error: 'getEffectIntensity not defined'};

    /* Build a fake stream */
    let stream;
    try {
        const ac = new AudioContext();
        const osc = ac.createOscillator();
        const dest = ac.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        stream = dest.stream;
    } catch (e) {
        return {ok: false, error: 'AudioContext unavailable: ' + e.message};
    }

    VoiceChanger.init(stream);

    /* setEffectIntensity clamps to [0, 1] */
    VoiceChanger.setEffectIntensity(0.75);
    if (Math.abs(VoiceChanger.getEffectIntensity() - 0.75) > 0.001) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setEffectIntensity(0.75) not stored correctly'};
    }
    VoiceChanger.setEffectIntensity(5);
    if (VoiceChanger.getEffectIntensity() !== 1) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setEffectIntensity(5) should clamp to 1, got ' + VoiceChanger.getEffectIntensity()};
    }
    VoiceChanger.setEffectIntensity(-1);
    if (VoiceChanger.getEffectIntensity() !== 0) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setEffectIntensity(-1) should clamp to 0, got ' + VoiceChanger.getEffectIntensity()};
    }

    /* Switching intensity on persona modes must not throw */
    VoiceChanger.setEffectIntensity(0.5);
    const personaModes = ['voice1', 'voice2', 'voice3'];
    for (const m of personaModes) {
        try {
            VoiceChanger.setMode(m);
            VoiceChanger.setEffectIntensity(0.8);
        } catch (e) {
            VoiceChanger.destroy();
            return {ok: false, error: 'setEffectIntensity threw on mode ' + m + ': ' + e.message};
        }
    }

    VoiceChanger.destroy();
    return {ok: true};
}
"""


def test_voice_changer_monitor_toggle(voice_changer_page):
    """toggleMonitor() must enable/disable the monitor and getMonitorEnabled() must reflect it."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_MONITOR_JS)
    assert result["ok"], result.get("error", "unknown error")


def test_voice_changer_volume_and_mic_gain(voice_changer_page):
    """setMonitorVolume() and setMicGain() must clamp values and persist them."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_VOLUME_GAIN_JS)
    assert result["ok"], result.get("error", "unknown error")


def test_voice_changer_init_idempotent(voice_changer_page):
    """Calling init() twice must not throw and must return a valid processed stream."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_INIT_IDEMPOTENT_JS)
    assert result["ok"], result.get("error", "unknown error")


def test_voice_changer_effect_intensity(voice_changer_page):
    """setEffectIntensity() must clamp to [0,1], persist, and not throw on persona modes."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_INTENSITY_JS)
    assert result["ok"], result.get("error", "unknown error")


# ---------------------------------------------------------------------------
# Combined-effects API tests
# ---------------------------------------------------------------------------

_VOICE_CHANGER_COMBINED_EFFECTS_JS = """
async () => {
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};
    if (typeof VoiceChanger.setEffectLevel !== 'function')
        return {ok: false, error: 'setEffectLevel not defined'};
    if (typeof VoiceChanger.getEffectLevels !== 'function')
        return {ok: false, error: 'getEffectLevels not defined'};
    if (typeof VoiceChanger.toggleEffect !== 'function')
        return {ok: false, error: 'toggleEffect not defined'};

    let stream;
    try {
        const ac = new AudioContext();
        const osc = ac.createOscillator();
        const dest = ac.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        stream = dest.stream;
    } catch (e) {
        return {ok: false, error: 'AudioContext unavailable: ' + e.message};
    }

    VoiceChanger.init(stream);

    /* All levels should start at 0 */
    const initial = VoiceChanger.getEffectLevels();
    const nonZero = Object.values(initial).filter(v => v !== 0);
    if (nonZero.length > 0) {
        VoiceChanger.destroy();
        return {ok: false, error: 'Expected all effectLevels to be 0 after init, got: ' + JSON.stringify(initial)};
    }

    /* setEffectLevel(mode, level) updates only that mode */
    VoiceChanger.setEffectLevel('deep', 0.6);
    const levels1 = VoiceChanger.getEffectLevels();
    if (Math.abs(levels1['deep'] - 0.6) > 0.001) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setEffectLevel deep 0.6 not stored; got ' + levels1['deep']};
    }
    if (levels1['echo'] !== 0) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setEffectLevel deep should not affect echo; echo=' + levels1['echo']};
    }

    /* Two effects can be active simultaneously */
    VoiceChanger.setEffectLevel('echo', 0.4);
    const levels2 = VoiceChanger.getEffectLevels();
    if (Math.abs(levels2['deep'] - 0.6) > 0.001 || Math.abs(levels2['echo'] - 0.4) > 0.001) {
        VoiceChanger.destroy();
        return {ok: false, error: 'Expected deep=0.6 and echo=0.4, got: ' + JSON.stringify(levels2)};
    }

    /* setEffectLevel clamps to [0,1] */
    VoiceChanger.setEffectLevel('deep', 5);
    if (VoiceChanger.getEffectLevels()['deep'] !== 1) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setEffectLevel(5) should clamp to 1'};
    }
    VoiceChanger.setEffectLevel('deep', -1);
    if (VoiceChanger.getEffectLevels()['deep'] !== 0) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setEffectLevel(-1) should clamp to 0'};
    }

    /* toggleEffect: off → on at globalIntensity */
    VoiceChanger.setEffectLevel('robot', 0);
    const toggled = VoiceChanger.toggleEffect('robot');
    if (toggled <= 0) {
        VoiceChanger.destroy();
        return {ok: false, error: 'toggleEffect on robot (off→on) should return > 0, got ' + toggled};
    }
    if (VoiceChanger.getEffectLevels()['robot'] !== toggled) {
        VoiceChanger.destroy();
        return {ok: false, error: 'toggleEffect did not update effectLevels.robot'};
    }

    /* toggleEffect: on → off */
    const toggled2 = VoiceChanger.toggleEffect('robot');
    if (toggled2 !== 0) {
        VoiceChanger.destroy();
        return {ok: false, error: 'toggleEffect on robot (on→off) should return 0, got ' + toggled2};
    }

    /* setEffectLevel(mode, 0) bypasses that effect; getProcessedStream still valid */
    VoiceChanger.setEffectLevel('echo', 0);
    const ps = VoiceChanger.getProcessedStream();
    if (!ps || (ps.getAudioTracks && ps.getAudioTracks().length === 0)) {
        VoiceChanger.destroy();
        return {ok: false, error: 'getProcessedStream() invalid after setEffectLevel to 0'};
    }

    /* destroy() resets all effectLevels to 0 */
    VoiceChanger.setEffectLevel('chipmunk', 0.7);
    VoiceChanger.destroy();
    const afterDestroy = VoiceChanger.getEffectLevels();
    const nonZeroAfter = Object.values(afterDestroy).filter(v => v !== 0);
    if (nonZeroAfter.length > 0) {
        return {ok: false, error: 'effectLevels not reset to 0 after destroy: ' + JSON.stringify(afterDestroy)};
    }

    return {ok: true};
}
"""

_VOICE_CHANGER_ALL_EFFECTS_COMBINED_JS = """
async () => {
    if (typeof VoiceChanger === 'undefined') return {ok: false, error: 'VoiceChanger not defined'};

    let stream;
    try {
        const ac = new AudioContext();
        const osc = ac.createOscillator();
        const dest = ac.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        stream = dest.stream;
    } catch (e) {
        return {ok: false, error: 'AudioContext unavailable: ' + e.message};
    }

    VoiceChanger.init(stream);

    /* Enable all 7 effects simultaneously — must not throw */
    const effectModes = ['deep', 'chipmunk', 'robot', 'echo', 'voice1', 'voice2', 'voice3'];
    try {
        for (const m of effectModes) {
            VoiceChanger.setEffectLevel(m, 0.5);
        }
    } catch (e) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setEffectLevel threw when combining all effects: ' + e.message};
    }

    /* All levels should be 0.5 */
    const levels = VoiceChanger.getEffectLevels();
    for (const m of effectModes) {
        if (Math.abs(levels[m] - 0.5) > 0.001) {
            VoiceChanger.destroy();
            return {ok: false, error: 'Expected level 0.5 for ' + m + ', got ' + levels[m]};
        }
    }

    /* Processed stream must still be valid */
    const ps = VoiceChanger.getProcessedStream();
    if (!ps) {
        VoiceChanger.destroy();
        return {ok: false, error: 'getProcessedStream() null with all effects combined'};
    }
    const tracks = ps.getAudioTracks ? ps.getAudioTracks() : [];
    if (tracks.length === 0) {
        VoiceChanger.destroy();
        return {ok: false, error: 'getProcessedStream() has no audio tracks with all effects combined'};
    }

    /* Disabling one effect at a time down to 0 should not throw */
    try {
        for (const m of effectModes) {
            VoiceChanger.setEffectLevel(m, 0);
        }
    } catch (e) {
        VoiceChanger.destroy();
        return {ok: false, error: 'setEffectLevel(0) threw when removing effects: ' + e.message};
    }

    VoiceChanger.destroy();
    return {ok: true};
}
"""


def test_voice_changer_combined_effects_api(voice_changer_page):
    """setEffectLevel/getEffectLevels/toggleEffect must support independent per-effect levels."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_COMBINED_EFFECTS_JS)
    assert result["ok"], result.get("error", "unknown error")


def test_voice_changer_all_effects_combined(voice_changer_page):
    """All 7 effects active simultaneously must not throw and keep the stream valid."""
    result = voice_changer_page.evaluate(_VOICE_CHANGER_ALL_EFFECTS_COMBINED_JS)
    assert result["ok"], result.get("error", "unknown error")


def test_video_room_includes_voice_controller_ui():
    """Video room page should include the in-call voice controller UI and script wiring."""
    html = (ROOT / "src/pages/video-room.html").read_text(encoding="utf-8")

    required_snippets = [
        'id="btn-voice-changer"',
        'id="voice-effects-panel"',
        'id="effect-sliders-container"',
        'id="btn-monitor"',
        'id="slider-monitor-volume"',
        'id="slider-mic-gain"',
        'src="js/voice-changer.js"',
    ]
    for snippet in required_snippets:
        assert snippet in html, f"Expected snippet missing in video-room.html: {snippet}"


def test_video_chat_includes_prejoin_voice_controller_ui():
    """Video chat lobby should include a pre-join voice controller and VoiceChanger script."""
    html = (ROOT / "src/pages/video-chat.html").read_text(encoding="utf-8")

    required_snippets = [
        'id="prejoin-voice-panel"',
        'data-lobby-voice-mode="normal"',
        'id="prejoin-effect-sliders-container"',
        'id="btn-preview-monitor"',
        'id="slider-preview-monitor-volume"',
        'id="slider-preview-mic-gain"',
        'src="js/voice-changer.js"',
    ]
    for snippet in required_snippets:
        assert snippet in html, f"Expected snippet missing in video-chat.html: {snippet}"


def test_video_room_peerjs_script_has_no_sri_integrity():
    """PeerJS CDN script should not use stale SRI that can block script execution in production."""
    html = (ROOT / "src/pages/video-room.html").read_text(encoding="utf-8")
    match = re.search(
        r'<script\b[^>]*src="https://unpkg\.com/peerjs@1\.5\.2/dist/peerjs\.min\.js"[^>]*>',
        html,
    )
    assert match, "PeerJS script tag missing in video-room.html"
    assert "integrity=" not in match.group(0), (
        "PeerJS script tag should not include integrity attribute; stale SRI breaks production loading"
    )
