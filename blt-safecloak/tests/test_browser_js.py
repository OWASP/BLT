"""
Browser-based JavaScript unit tests for BLT-SafeCloak client-side modules.

Exercises in a headless Chromium browser:
  - Crypto    – generateKey, encrypt/decrypt round-trip, sha256, randomId,
                saveEncrypted / loadEncrypted, importKey / exportKey round-trip
  - ThemeManager – toggle, getCurrentTheme, localStorage persistence
  - ConsentManager – record (creates hash), verifyEntry integrity check,
                     getLog, default field values
  - NotesApp AI  – summarize, extractKeyPoints, extractActionItems, wordFrequency
  - ui.js helpers – formatDateTime, formatDateShort, showToast

A minimal HTTP server (no PeerJS dependency) is started once per test session
to serve the notes and consent pages with their static assets.  A single
Playwright browser instance opens both pages for the duration of the test
module, avoiding asyncio event-loop conflicts that arise from creating multiple
sync_playwright() contexts in the same module.

Local setup::

    npm install
    pip install -r requirements-dev.txt
    playwright install chromium --with-deps

Then run::

    pytest tests/test_browser_js.py -v
"""

import http.server
import re
import socket
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent

# ── CDN-stripping regexes ─────────────────────────────────────────────────────
_TAILWIND_SCRIPT_RE = re.compile(
    r'<script\b[^>]*\bsrc="https://cdn\.tailwindcss\.com[^"]*"[^>]*>\s*</script>',
    re.DOTALL,
)
_TAILWIND_CONFIG_RE = re.compile(
    r'<script>\s*tailwind\.config\s*=\s*\{.*?\};\s*</script>',
    re.DOTALL,
)
_GOOGLE_FONTS_RE = re.compile(
    r'<link\b[^>]*\bhref="https://fonts\.(googleapis|gstatic)\.com[^"]*"[^>]*/?>',
    re.DOTALL,
)
_FONT_AWESOME_RE = re.compile(
    r'<link\b[^>]*\bhref="https://cdnjs\.cloudflare\.com[^"]*"[^>]*/?>',
    re.DOTALL,
)

_PAGES = {
    '/notes': 'src/pages/notes.html',
    '/consent': 'src/pages/consent.html',
}

_MIME = {
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
}

_PUBLIC_FILES: dict[str, Path] = {
    '/' + f.relative_to(ROOT / 'public').as_posix(): f
    for f in (ROOT / 'public').rglob('*')
    if f.is_file()
}

TIMEOUT_MS = 30_000

_BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
]


def _strip_cdn(html: str) -> str:
    html = _TAILWIND_SCRIPT_RE.sub('', html)
    html = _TAILWIND_CONFIG_RE.sub('', html)
    html = _GOOGLE_FONTS_RE.sub('', html)
    html = _FONT_AWESOME_RE.sub('', html)
    return html


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class _MinimalHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = self.path.split('?')[0]
        if path in _PAGES:
            raw = (ROOT / _PAGES[path]).read_bytes()
            data = _strip_cdn(raw.decode('utf-8')).encode('utf-8')
            self._respond(200, 'text/html; charset=utf-8', data)
            return
        file_path = _PUBLIC_FILES.get(path)
        if file_path is not None:
            data = file_path.read_bytes()
            ct = _MIME.get(file_path.suffix, 'application/octet-stream')
            self._respond(200, ct, data)
            return
        self._respond(404, 'text/plain', b'Not found')

    def _respond(self, status, content_type, body):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


# ── Session-scoped HTTP server ────────────────────────────────────────────────


@pytest.fixture(scope='session')
def js_test_server_url():
    server = _ThreadingTCPServer(('127.0.0.1', 0), _MinimalHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield f'http://127.0.0.1:{port}'
    finally:
        server.shutdown()
        server.server_close()


# ── Single module-scoped Playwright fixture (both pages in one browser) ───────


@pytest.fixture(scope='module')
def browser_pages(js_test_server_url):
    """Open notes and consent pages in a single browser session.

    Yielding both pages from one playwright() context avoids the
    'Sync API inside asyncio loop' error that occurs when two separate
    module-scoped sync_playwright() contexts live in the same test module.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=_BROWSER_ARGS)
        try:
            notes_ctx = browser.new_context()
            notes_pg = notes_ctx.new_page()
            notes_pg.goto(f'{js_test_server_url}/notes')
            notes_pg.wait_for_function('typeof NotesApp !== "undefined"', timeout=TIMEOUT_MS)
            notes_pg.wait_for_function('typeof Crypto !== "undefined"', timeout=TIMEOUT_MS)
            notes_pg.wait_for_function('typeof ThemeManager !== "undefined"', timeout=TIMEOUT_MS)

            consent_ctx = browser.new_context()
            consent_pg = consent_ctx.new_page()
            consent_pg.goto(f'{js_test_server_url}/consent')
            consent_pg.wait_for_function('typeof ConsentManager !== "undefined"',
                                         timeout=TIMEOUT_MS)
            consent_pg.wait_for_function('typeof Crypto !== "undefined"', timeout=TIMEOUT_MS)

            yield {'notes': notes_pg, 'consent': consent_pg}
        finally:
            browser.close()


# Convenience fixtures that extract a single page from browser_pages.

@pytest.fixture(scope='module')
def notes_page(browser_pages):
    return browser_pages['notes']


@pytest.fixture(scope='module')
def consent_page(browser_pages):
    return browser_pages['consent']


# ── Crypto module tests ───────────────────────────────────────────────────────

_CRYPTO_GENERATE_KEY_JS = """
async () => {
    try {
        const key = await Crypto.generateKey();
        if (!key) return {ok: false, error: 'generateKey() returned falsy'};
        const b64 = await Crypto.exportKey(key);
        if (typeof b64 !== 'string' || b64.length === 0)
            return {ok: false, error: 'exportKey() returned empty string'};
        const key2 = await Crypto.importKey(b64);
        if (!key2) return {ok: false, error: 'importKey() returned falsy'};
        return {ok: true};
    } catch(e) {
        return {ok: false, error: e.message};
    }
}
"""

_CRYPTO_ENCRYPT_DECRYPT_JS = """
async () => {
    try {
        const key = await Crypto.generateKey();
        const plaintext = 'Hello, BLT-SafeCloak! \\u{1F512}';
        const encrypted = await Crypto.encrypt(plaintext, key);
        if (!encrypted.iv || !encrypted.ciphertext)
            return {ok: false, error: 'encrypt() did not return {iv, ciphertext}'};
        const decrypted = await Crypto.decrypt(encrypted, key);
        if (decrypted !== plaintext)
            return {ok: false, error: 'round-trip failed: got "' + decrypted + '"'};
        return {ok: true};
    } catch(e) {
        return {ok: false, error: e.message};
    }
}
"""

_CRYPTO_DIFFERENT_KEYS_JS = """
async () => {
    try {
        const key1 = await Crypto.generateKey();
        const key2 = await Crypto.generateKey();
        const encrypted = await Crypto.encrypt('secret', key1);
        let threw = false;
        try { await Crypto.decrypt(encrypted, key2); } catch(_) { threw = true; }
        if (!threw) return {ok: false, error: 'Decrypt with wrong key should have thrown'};
        return {ok: true};
    } catch(e) {
        return {ok: false, error: e.message};
    }
}
"""

_CRYPTO_SHA256_JS = """
async () => {
    try {
        const h1 = await Crypto.sha256('test-input');
        if (typeof h1 !== 'string' || h1.length !== 64)
            return {ok: false, error: 'sha256 must return 64 hex chars, got: ' + h1};
        const h2 = await Crypto.sha256('test-input');
        if (h1 !== h2) return {ok: false, error: 'sha256 is not deterministic'};
        const h3 = await Crypto.sha256('other-input');
        if (h1 === h3) return {ok: false, error: 'sha256 collision for different inputs'};
        return {ok: true};
    } catch(e) {
        return {ok: false, error: e.message};
    }
}
"""

_CRYPTO_RANDOM_ID_JS = """
() => {
    const id1 = Crypto.randomId();
    const id2 = Crypto.randomId();
    if (typeof id1 !== 'string' || id1.length === 0)
        return {ok: false, error: 'randomId() returned empty/non-string'};
    if (id1 === id2)
        return {ok: false, error: 'randomId() returned same value twice (very unlikely)'};
    const id16 = Crypto.randomId(16);
    if (id16.length !== 16)
        return {ok: false, error: 'randomId(16) length wrong: ' + id16.length};
    return {ok: true};
}
"""

_CRYPTO_SAVE_LOAD_JS = """
async () => {
    const KEY = 'blt-test-save-load-' + Date.now();
    const data = {message: 'encrypted-note', num: 42, nested: {a: 1}};
    const pass = 'test-passphrase-xyz';
    try {
        await Crypto.saveEncrypted(KEY, data, pass);
        const loaded = await Crypto.loadEncrypted(KEY, pass);
        if (!loaded) return {ok: false, error: 'loadEncrypted returned null'};
        if (loaded.message !== data.message)
            return {ok: false, error: 'message mismatch: ' + JSON.stringify(loaded)};
        if (loaded.num !== data.num)
            return {ok: false, error: 'num mismatch'};
        if (loaded.nested.a !== 1)
            return {ok: false, error: 'nested field mismatch'};
        const bad = await Crypto.loadEncrypted(KEY, 'wrong-pass');
        if (bad !== null)
            return {ok: false, error: 'wrong passphrase should return null'};
        localStorage.removeItem(KEY);
        return {ok: true};
    } catch(e) {
        return {ok: false, error: e.message};
    }
}
"""

_CRYPTO_LOAD_MISSING_KEY_JS = """
async () => {
    const KEY = 'blt-test-nonexistent-' + Date.now();
    const result = await Crypto.loadEncrypted(KEY, 'pass');
    if (result !== null) return {ok: false, error: 'Expected null for missing key'};
    return {ok: true};
}
"""

_CRYPTO_DERIVE_KEY_DIFFERS_JS = """
async () => {
    try {
        const k1 = await Crypto.deriveKey('passA', 'salt-1');
        const k2 = await Crypto.deriveKey('passB', 'salt-1');
        const b1 = await Crypto.exportKey(k1);
        const b2 = await Crypto.exportKey(k2);
        if (b1 === b2)
            return {ok: false, error: 'Different passphrases produced the same derived key'};
        return {ok: true};
    } catch(e) {
        return {ok: false, error: e.message};
    }
}
"""


def test_crypto_generate_and_roundtrip_export_import(notes_page):
    """generateKey/exportKey/importKey must produce a consistent round-trip."""
    result = notes_page.evaluate(_CRYPTO_GENERATE_KEY_JS)
    assert result['ok'], result.get('error')


def test_crypto_encrypt_decrypt_roundtrip(notes_page):
    """encrypt/decrypt must round-trip any plaintext including Unicode."""
    result = notes_page.evaluate(_CRYPTO_ENCRYPT_DECRYPT_JS)
    assert result['ok'], result.get('error')


def test_crypto_decrypt_with_wrong_key_fails(notes_page):
    """Decrypting with a different key must raise an error."""
    result = notes_page.evaluate(_CRYPTO_DIFFERENT_KEYS_JS)
    assert result['ok'], result.get('error')


def test_crypto_sha256_returns_hex_string(notes_page):
    """sha256 must return a 64-character hex string and be deterministic."""
    result = notes_page.evaluate(_CRYPTO_SHA256_JS)
    assert result['ok'], result.get('error')


def test_crypto_random_id_unique_and_correct_length(notes_page):
    """randomId() must return a unique string of the requested length."""
    result = notes_page.evaluate(_CRYPTO_RANDOM_ID_JS)
    assert result['ok'], result.get('error')


def test_crypto_save_encrypted_and_load_roundtrip(notes_page):
    """saveEncrypted / loadEncrypted must persist and restore a JSON object."""
    result = notes_page.evaluate(_CRYPTO_SAVE_LOAD_JS)
    assert result['ok'], result.get('error')


def test_crypto_load_missing_key_returns_null(notes_page):
    """loadEncrypted for a missing storage key must return null."""
    result = notes_page.evaluate(_CRYPTO_LOAD_MISSING_KEY_JS)
    assert result['ok'], result.get('error')


def test_crypto_derive_key_differs_by_passphrase(notes_page):
    """deriveKey with different passphrases must produce different keys."""
    result = notes_page.evaluate(_CRYPTO_DERIVE_KEY_DIFFERS_JS)
    assert result['ok'], result.get('error')


# ── ThemeManager tests ────────────────────────────────────────────────────────
# NOTE: applyTheme() is an internal (non-exported) function.  Theme tests use
# only the public API: toggle(), getCurrentTheme(), and localStorage inspection.

_THEME_GET_CURRENT_JS = """
() => {
    if (typeof ThemeManager === 'undefined')
        return {ok: false, error: 'ThemeManager not defined'};
    const theme = ThemeManager.getCurrentTheme();
    if (theme !== 'light' && theme !== 'dark')
        return {ok: false, error: 'getCurrentTheme() returned: ' + theme};
    return {ok: true, theme};
}
"""

_THEME_TOGGLE_JS = """
() => {
    const before = ThemeManager.getCurrentTheme();
    ThemeManager.toggle();
    const after = ThemeManager.getCurrentTheme();
    if (before === after)
        return {ok: false, error: 'toggle() did not change theme'};
    const expected = before === 'light' ? 'dark' : 'light';
    if (after !== expected)
        return {ok: false, error: 'Unexpected theme after toggle: ' + after};
    ThemeManager.toggle();  // Restore original state
    return {ok: true, before, after};
}
"""

_THEME_DARK_CLASS_JS = """
() => {
    // Force dark via toggle if needed, then verify class
    const initial = ThemeManager.getCurrentTheme();
    if (initial !== 'dark') ThemeManager.toggle();
    const hasDark = document.documentElement.classList.contains('dark');
    if (!hasDark)
        return {ok: false, error: "'dark' class not added to <html> when dark mode is active"};
    // Back to light
    if (ThemeManager.getCurrentTheme() === 'dark') ThemeManager.toggle();
    const hasLight = !document.documentElement.classList.contains('dark');
    if (!hasLight)
        return {ok: false, error: "'dark' class still present after switching to light"};
    return {ok: true};
}
"""

_THEME_PERSISTENCE_JS = """
() => {
    const KEY = 'blt-theme-preference';
    // Switch to dark and check storage
    const initial = ThemeManager.getCurrentTheme();
    if (initial !== 'dark') ThemeManager.toggle();
    const storedDark = localStorage.getItem(KEY);
    if (storedDark !== 'dark')
        return {ok: false, error: 'Expected dark in localStorage, got: ' + storedDark};
    // Switch to light and check storage
    ThemeManager.toggle();
    const storedLight = localStorage.getItem(KEY);
    if (storedLight !== 'light')
        return {ok: false, error: 'Expected light in localStorage, got: ' + storedLight};
    return {ok: true};
}
"""


def test_theme_manager_get_current_theme(notes_page):
    """ThemeManager.getCurrentTheme() must return 'light' or 'dark'."""
    result = notes_page.evaluate(_THEME_GET_CURRENT_JS)
    assert result['ok'], result.get('error')


def test_theme_manager_toggle_switches_theme(notes_page):
    """toggle() must flip the current theme and restore it on the second call."""
    result = notes_page.evaluate(_THEME_TOGGLE_JS)
    assert result['ok'], result.get('error')


def test_theme_manager_dark_adds_class_to_html(notes_page):
    """Dark mode must add the 'dark' class to <html>; light mode must remove it."""
    result = notes_page.evaluate(_THEME_DARK_CLASS_JS)
    assert result['ok'], result.get('error')


def test_theme_manager_persists_to_local_storage(notes_page):
    """toggle() must persist the new theme to localStorage."""
    result = notes_page.evaluate(_THEME_PERSISTENCE_JS)
    assert result['ok'], result.get('error')


# ── ConsentManager tests ──────────────────────────────────────────────────────

_CONSENT_RECORD_JS = """
async () => {
    if (typeof ConsentManager === 'undefined')
        return {ok: false, error: 'ConsentManager not defined'};
    const before = ConsentManager.getLog().length;
    const entry = await ConsentManager.record({
        type: 'given',
        name: 'Test User',
        details: 'Consented to recording',
        purpose: 'Testing',
    });
    if (!entry) return {ok: false, error: 'record() returned falsy'};
    if (entry.type !== 'given')
        return {ok: false, error: 'entry.type mismatch: ' + entry.type};
    if (entry.name !== 'Test User')
        return {ok: false, error: 'entry.name mismatch'};
    if (!entry.hash || entry.hash === 'hash-unavailable')
        return {ok: false, error: 'hash missing or unavailable: ' + entry.hash};
    if (entry.hash.length !== 64)
        return {ok: false, error: 'hash length should be 64, got ' + entry.hash.length};
    if (!entry.isoTime)
        return {ok: false, error: 'entry.isoTime missing'};
    if (!entry.id)
        return {ok: false, error: 'entry.id missing'};
    const after = ConsentManager.getLog().length;
    if (after !== before + 1)
        return {ok: false, error: 'Log should grow by 1 (was ' + before + ', now ' + after + ')'};
    return {ok: true, entryId: entry.id};
}
"""

_CONSENT_VERIFY_JS = """
async () => {
    const entry = await ConsentManager.record({
        type: 'withdrawn',
        name: 'Verify User',
        details: 'Withdrawal test',
        purpose: 'Integrity check',
    });
    try {
        await ConsentManager.verifyEntry(entry.id);
    } catch(e) {
        return {ok: false, error: 'verifyEntry threw: ' + e.message};
    }
    return {ok: true};
}
"""

_CONSENT_GET_LOG_JS = """
() => {
    const log = ConsentManager.getLog();
    if (!Array.isArray(log)) return {ok: false, error: 'getLog() must return an array'};
    return {ok: true, length: log.length};
}
"""

_CONSENT_DEFAULTS_JS = """
async () => {
    const entry = await ConsentManager.record({});
    if (entry.type !== 'recorded')
        return {ok: false, error: 'default type should be recorded, got: ' + entry.type};
    if (entry.name !== 'Unnamed event')
        return {ok: false, error: 'default name mismatch: ' + entry.name};
    return {ok: true};
}
"""

_CONSENT_MULTIPLE_TYPES_JS = """
async () => {
    for (const type of ['given', 'withdrawn', 'recorded']) {
        const entry = await ConsentManager.record({type, name: 'Type Test'});
        if (entry.type !== type)
            return {ok: false, error: 'Expected type ' + type + ', got: ' + entry.type};
    }
    return {ok: true};
}
"""


def test_consent_record_creates_entry_with_hash(consent_page):
    """record() must create a log entry with a valid SHA-256 hash."""
    result = consent_page.evaluate(_CONSENT_RECORD_JS)
    assert result['ok'], result.get('error')


def test_consent_verify_entry_does_not_throw(consent_page):
    """verifyEntry() must run without throwing for a valid entry."""
    result = consent_page.evaluate(_CONSENT_VERIFY_JS)
    assert result['ok'], result.get('error')


def test_consent_get_log_returns_array(consent_page):
    """getLog() must return an array."""
    result = consent_page.evaluate(_CONSENT_GET_LOG_JS)
    assert result['ok'], result.get('error')


def test_consent_record_uses_defaults_for_missing_fields(consent_page):
    """record() with an empty object should use default type and name."""
    result = consent_page.evaluate(_CONSENT_DEFAULTS_JS)
    assert result['ok'], result.get('error')


def test_consent_record_stores_all_type_values(consent_page):
    """record() must accept all three consent types: given, withdrawn, recorded."""
    result = consent_page.evaluate(_CONSENT_MULTIPLE_TYPES_JS)
    assert result['ok'], result.get('error')


# ── Notes AI feature tests ────────────────────────────────────────────────────
# Notes.js AI functions (summarize, extractKeyPoints, extractActionItems,
# wordFrequency) are internal to the IIFE.  We exercise them via the exported
# API: create a note, set its content directly through the notes() array
# reference, then click the corresponding AI toolbar button.

_NOTES_PREPARE_JS = """
async () => {
    // Create a fresh note and inject content directly into the notes array
    const note = NotesApp.createNote();
    const arr = NotesApp.notes();
    arr[0].content = 'This is an important note. It must be recorded. The action must be taken. We should review this content carefully. Important decisions require consent and review.';
    return {ok: true, id: note.id};
}
"""

_NOTES_SUMMARIZE_JS = """
async () => {
    // Prepare note content – multi-sentence text exercises the full summarize path
    // (previously a .trim() vs indexOf mismatch caused a TypeError for multi-sentence text)
    const note = NotesApp.createNote();
    const arr = NotesApp.notes();
    arr[0].content = 'Security is critical for all applications. Privacy must be protected at all times. Encryption ensures that sensitive data remains secure. Review these requirements carefully before deployment.';

    const btn = document.getElementById('btn-summarize');
    const out = document.getElementById('ai-output');
    if (!btn) return {ok: false, error: '#btn-summarize not found'};
    if (!out) return {ok: false, error: '#ai-output not found'};

    btn.click();

    if (!out.textContent || out.textContent.trim() === '')
        return {ok: false, error: '#ai-output empty after summarize click'};
    if (!out.textContent.includes('Summary'))
        return {ok: false, error: 'Missing Summary prefix: ' + out.textContent.slice(0, 80)};
    return {ok: true, output: out.textContent.slice(0, 80)};
}
"""

_NOTES_KEYPOINTS_JS = """
async () => {
    const arr = NotesApp.notes();
    if (arr.length === 0) NotesApp.createNote();
    arr[0].content = 'You must complete the task. This is important for the project. Action required: review and consent. Key decision needed.';

    const btn = document.getElementById('btn-keypoints');
    const out = document.getElementById('ai-output');
    if (!btn || !out) return {ok: false, error: 'DOM elements missing'};
    btn.click();
    if (!out.textContent.trim())
        return {ok: false, error: '#ai-output empty after keypoints'};
    return {ok: true};
}
"""

_NOTES_ACTION_ITEMS_JS = """
async () => {
    const arr = NotesApp.notes();
    if (arr.length === 0) NotesApp.createNote();
    arr[0].content = 'todo: fix the bug. action: review PR by Friday. follow up with team. assign tickets.';

    const btn = document.getElementById('btn-actions');
    const out = document.getElementById('ai-output');
    if (!btn || !out) return {ok: false, error: 'DOM elements missing'};
    btn.click();
    if (!out.textContent.trim())
        return {ok: false, error: '#ai-output empty after action items'};
    return {ok: true};
}
"""

_NOTES_WORD_FREQ_JS = """
async () => {
    const arr = NotesApp.notes();
    if (arr.length === 0) NotesApp.createNote();
    arr[0].content = 'privacy privacy privacy secure secure encryption encryption notes meeting notes';

    const btn = document.getElementById('btn-keywords');
    const out = document.getElementById('ai-output');
    if (!btn || !out) return {ok: false, error: 'DOM elements missing'};
    btn.click();
    if (!out.textContent.trim())
        return {ok: false, error: '#ai-output empty after keywords'};
    if (!out.textContent.includes('privacy'))
        return {ok: false, error: "'privacy' not in keyword output: " + out.textContent};
    return {ok: true};
}
"""

_NOTES_CREATE_JS = """
() => {
    const before = NotesApp.notes().length;
    const note = NotesApp.createNote();
    const after = NotesApp.notes().length;
    if (!note || !note.id) return {ok: false, error: 'createNote() returned invalid note'};
    if (after !== before + 1)
        return {ok: false, error: 'notes array should grow by 1 (was ' + before + ', now ' + after + ')'};
    return {ok: true, id: note.id};
}
"""


def test_notes_create_note_adds_to_array(notes_page):
    """createNote() must return a note object and add it to the notes array."""
    result = notes_page.evaluate(_NOTES_CREATE_JS)
    assert result['ok'], result.get('error')


def test_notes_summarize_populates_ai_output(notes_page):
    """Clicking 'Summarize' on a note with content must populate #ai-output."""
    result = notes_page.evaluate(_NOTES_SUMMARIZE_JS)
    assert result['ok'], result.get('error')


def test_notes_keypoints_populates_ai_output(notes_page):
    """Clicking 'Key Points' on a note must populate #ai-output."""
    result = notes_page.evaluate(_NOTES_KEYPOINTS_JS)
    assert result['ok'], result.get('error')


def test_notes_action_items_populates_ai_output(notes_page):
    """Clicking 'Action Items' on a note with action words must populate #ai-output."""
    result = notes_page.evaluate(_NOTES_ACTION_ITEMS_JS)
    assert result['ok'], result.get('error')


def test_notes_word_frequency_includes_top_keyword(notes_page):
    """Clicking 'Keywords' must show the most frequent word in #ai-output."""
    result = notes_page.evaluate(_NOTES_WORD_FREQ_JS)
    assert result['ok'], result.get('error')


# ── ui.js helper tests ────────────────────────────────────────────────────────

_UI_FORMAT_DATE_TIME_JS = """
() => {
    if (typeof formatDateTime !== 'function')
        return {ok: false, error: 'formatDateTime not defined'};
    const result = formatDateTime(1700000000000);
    if (typeof result !== 'string' || result.trim() === '')
        return {ok: false, error: 'formatDateTime returned empty: ' + result};
    return {ok: true, result};
}
"""

_UI_FORMAT_DATE_SHORT_JS = """
() => {
    if (typeof formatDateShort !== 'function')
        return {ok: false, error: 'formatDateShort not defined'};
    const nowMs = Date.now();

    const justNow = formatDateShort(nowMs - 10000);
    if (justNow !== 'just now')
        return {ok: false, error: 'Expected "just now", got: ' + justNow};

    const twoMin = formatDateShort(nowMs - 2 * 60 * 1000);
    if (!twoMin.includes('m ago'))
        return {ok: false, error: 'Expected "Xm ago", got: ' + twoMin};

    const twoHrs = formatDateShort(nowMs - 2 * 3600 * 1000);
    if (!twoHrs.includes('h ago'))
        return {ok: false, error: 'Expected "Xh ago", got: ' + twoHrs};

    return {ok: true};
}
"""

_UI_SHOW_TOAST_JS = """
() => {
    if (typeof showToast !== 'function')
        return {ok: false, error: 'showToast not defined'};
    try {
        showToast('Success!', 'success');
        showToast('Error!', 'error');
        showToast('Info!', 'info');
        showToast('Warning!', 'warning');
    } catch(e) {
        return {ok: false, error: 'showToast threw: ' + e.message};
    }
    const container = document.getElementById('toast-container');
    if (!container)
        return {ok: false, error: '#toast-container not found after showToast'};
    return {ok: true};
}
"""


def test_ui_format_date_time_returns_string(notes_page):
    """formatDateTime must return a non-empty locale string."""
    result = notes_page.evaluate(_UI_FORMAT_DATE_TIME_JS)
    assert result['ok'], result.get('error')


def test_ui_format_date_short_relative_labels(notes_page):
    """formatDateShort must return 'just now', 'Xm ago', and 'Xh ago' labels."""
    result = notes_page.evaluate(_UI_FORMAT_DATE_SHORT_JS)
    assert result['ok'], result.get('error')


def test_ui_show_toast_does_not_throw(notes_page):
    """showToast must create the toast container and not throw for all types."""
    result = notes_page.evaluate(_UI_SHOW_TOAST_JS)
    assert result['ok'], result.get('error')
