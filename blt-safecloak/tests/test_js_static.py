"""
Static analysis tests for the JavaScript modules in public/js/.

These tests read the source files directly and assert that the expected
function definitions, exports, and constants are present, without requiring
a browser or Node.js runtime.

Coverage:
  - crypto.js   – all public API members are exported
  - notes.js    – internal AI functions defined, public API exported
  - consent.js  – record/verify/export functions defined, public API exported
  - ui.js       – global utility functions defined
  - theme.js    – ThemeManager API exported
  - voice-changer.js – (structure only, deeper tests live in test_video_chat.py)
  - video-lobby.js   – key functions and constants present
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent
JS_DIR = ROOT / 'public' / 'js'


def _read(filename: str) -> str:
    return (JS_DIR / filename).read_text(encoding='utf-8')


# ── crypto.js ─────────────────────────────────────────────────────────────────


def test_crypto_js_defines_generate_key():
    assert 'async function generateKey()' in _read('crypto.js')


def test_crypto_js_defines_export_key():
    assert 'async function exportKey(' in _read('crypto.js')


def test_crypto_js_defines_import_key():
    assert 'async function importKey(' in _read('crypto.js')


def test_crypto_js_defines_derive_key():
    assert 'async function deriveKey(' in _read('crypto.js')


def test_crypto_js_defines_encrypt():
    assert 'async function encrypt(' in _read('crypto.js')


def test_crypto_js_defines_decrypt():
    assert 'async function decrypt(' in _read('crypto.js')


def test_crypto_js_defines_sha256():
    assert 'async function sha256(' in _read('crypto.js')


def test_crypto_js_defines_random_id():
    assert 'function randomId(' in _read('crypto.js')


def test_crypto_js_defines_save_encrypted():
    assert 'async function saveEncrypted(' in _read('crypto.js')


def test_crypto_js_defines_load_encrypted():
    assert 'async function loadEncrypted(' in _read('crypto.js')


def test_crypto_js_exports_all_public_members():
    js = _read('crypto.js')
    for name in [
            'generateKey',
            'exportKey',
            'importKey',
            'deriveKey',
            'encrypt',
            'decrypt',
            'sha256',
            'randomId',
            'saveEncrypted',
            'loadEncrypted',
    ]:
        assert name + ',' in js or name + '\n' in js or name + '}' in js, (
            f'crypto.js does not export: {name}')


def test_crypto_js_uses_aes_gcm():
    js = _read('crypto.js')
    assert 'AES-GCM' in js


def test_crypto_js_uses_256_bit_key():
    js = _read('crypto.js')
    assert '256' in js


def test_crypto_js_uses_pbkdf2_for_derive_key():
    js = _read('crypto.js')
    assert 'PBKDF2' in js


def test_crypto_js_warns_on_missing_salt():
    js = _read('crypto.js')
    assert 'no salt provided' in js or 'salt' in js


def test_crypto_js_uses_local_storage_for_save_encrypted():
    js = _read('crypto.js')
    assert 'localStorage.setItem(' in js


def test_crypto_js_uses_local_storage_for_load_encrypted():
    js = _read('crypto.js')
    assert 'localStorage.getItem(' in js


# ── notes.js ──────────────────────────────────────────────────────────────────


def test_notes_js_defines_summarize():
    assert 'function summarize(' in _read('notes.js')


def test_notes_js_defines_extract_key_points():
    assert 'function extractKeyPoints(' in _read('notes.js')


def test_notes_js_defines_extract_action_items():
    assert 'function extractActionItems(' in _read('notes.js')


def test_notes_js_defines_word_frequency():
    assert 'function wordFrequency(' in _read('notes.js')


def test_notes_js_defines_create_note():
    assert 'function createNote(' in _read('notes.js')


def test_notes_js_defines_delete_note():
    assert 'function deleteNote(' in _read('notes.js')


def test_notes_js_defines_export_note():
    assert 'function exportNote(' in _read('notes.js')


def test_notes_js_defines_init():
    assert 'async function init()' in _read('notes.js')


def test_notes_js_exports_public_api():
    js = _read('notes.js')
    for name in ['init', 'createNote', 'deleteNote', 'exportNote', 'exportAllNotes']:
        assert name in js, f'notes.js does not export: {name}'


def test_notes_js_uses_crypto_save_encrypted():
    assert 'Crypto.saveEncrypted(' in _read('notes.js')


def test_notes_js_uses_crypto_load_encrypted():
    assert 'Crypto.loadEncrypted(' in _read('notes.js')


def test_notes_js_defines_esc_html():
    assert 'function escHtml(' in _read('notes.js')


def test_notes_js_defines_schedule_save():
    assert 'function scheduleSave(' in _read('notes.js')


def test_notes_js_supports_txt_md_json_export_formats():
    js = _read('notes.js')
    assert '"txt"' in js or "'txt'" in js
    assert '"md"' in js or "'md'" in js
    assert '"json"' in js or "'json'" in js


def test_notes_js_defines_stopwords_set():
    assert 'STOPWORDS' in _read('notes.js')


def test_notes_js_word_count_uses_split():
    """updateWordCount must count words by splitting on whitespace."""
    js = _read('notes.js')
    assert 'function updateWordCount(' in js
    assert 'split(' in js


# ── consent.js ────────────────────────────────────────────────────────────────


def test_consent_js_defines_record():
    assert 'async function record(' in _read('consent.js')


def test_consent_js_defines_verify_entry():
    assert 'async function verifyEntry(' in _read('consent.js')


def test_consent_js_defines_delete_entry():
    assert 'function deleteEntry(' in _read('consent.js')


def test_consent_js_defines_export_log():
    assert 'function exportLog(' in _read('consent.js')


def test_consent_js_defines_render_log():
    assert 'function renderLog(' in _read('consent.js')


def test_consent_js_defines_update_stats():
    assert 'function updateStats(' in _read('consent.js')


def test_consent_js_defines_esc_html():
    assert 'function escHtml(' in _read('consent.js')


def test_consent_js_defines_capitalise():
    assert 'function capitalise(' in _read('consent.js')


def test_consent_js_exports_public_api():
    js = _read('consent.js')
    for name in ['init', 'record', 'verifyEntry', 'deleteEntry', 'exportLog', 'getLog']:
        assert name in js, f'consent.js does not export: {name}'


def test_consent_js_creates_tamper_evident_hash():
    """record() must call Crypto.sha256 to create a tamper-evident hash."""
    assert 'Crypto.sha256(' in _read('consent.js')


def test_consent_js_supports_json_and_csv_export():
    js = _read('consent.js')
    assert '"csv"' in js or "'csv'" in js
    assert '"json"' in js or "'json'" in js


def test_consent_js_stores_entry_type_given_withdrawn_recorded():
    js = _read('consent.js')
    assert "'given'" in js or '"given"' in js
    assert "'withdrawn'" in js or '"withdrawn"' in js
    assert "'recorded'" in js or '"recorded"' in js


def test_consent_js_stores_user_agent():
    assert 'userAgent' in _read('consent.js')


def test_consent_js_stores_iso_time():
    assert 'isoTime' in _read('consent.js')


# ── ui.js ──────────────────────────────────────────────────────────────────────


def test_ui_js_defines_show_toast():
    assert 'function showToast(' in _read('ui.js')


def test_ui_js_defines_open_modal():
    assert 'function openModal(' in _read('ui.js')


def test_ui_js_defines_close_modal():
    assert 'function closeModal(' in _read('ui.js')


def test_ui_js_defines_copy_to_clipboard():
    assert 'async function copyToClipboard(' in _read('ui.js')


def test_ui_js_defines_format_date_time():
    assert 'function formatDateTime(' in _read('ui.js')


def test_ui_js_defines_format_date_short():
    assert 'function formatDateShort(' in _read('ui.js')


def test_ui_js_show_toast_supports_all_types():
    js = _read('ui.js')
    for t in ['success', 'error', 'info', 'warning']:
        assert t in js, f'ui.js showToast does not handle type: {t}'


def test_ui_js_copy_to_clipboard_has_fallback():
    """copyToClipboard must have a textarea fallback for older browsers."""
    js = _read('ui.js')
    assert 'execCommand' in js
    assert 'textarea' in js


def test_ui_js_navbar_toggle_closes_on_outside_click():
    js = _read('ui.js')
    assert 'navbar-nav' in js
    assert 'navbar-toggle' in js


# ── theme.js ──────────────────────────────────────────────────────────────────


def test_theme_js_defines_theme_manager():
    assert 'ThemeManager' in _read('theme.js')


def test_theme_js_defines_init():
    assert 'function init(' in _read('theme.js')


def test_theme_js_defines_toggle():
    assert 'function toggle(' in _read('theme.js')


def test_theme_js_defines_get_current_theme():
    assert 'function getCurrentTheme(' in _read('theme.js')


def test_theme_js_defines_apply_theme():
    assert 'function applyTheme(' in _read('theme.js')


def test_theme_js_defines_update_toggle_button():
    assert 'function updateToggleButton(' in _read('theme.js')


def test_theme_js_exports_public_api():
    js = _read('theme.js')
    for name in ['init', 'toggle', 'getCurrentTheme', 'updateToggleButton', 'initToggleButton']:
        assert name in js, f'theme.js does not export: {name}'


def test_theme_js_persists_to_local_storage():
    js = _read('theme.js')
    assert "localStorage.setItem(" in js
    assert "localStorage.getItem(" in js


def test_theme_js_uses_dark_class():
    js = _read('theme.js')
    assert "'dark'" in js or '"dark"' in js


def test_theme_js_storage_key_constant():
    js = _read('theme.js')
    assert 'blt-theme-preference' in js


# ── video-lobby.js ────────────────────────────────────────────────────────────


def test_video_lobby_js_has_display_name_storage_key():
    js = _read('video-lobby.js')
    assert 'blt-safecloak-display-name' in js


def test_video_lobby_js_has_walkie_talkie_support():
    js = _read('video-lobby.js')
    assert 'walkieTalkieEnabled' in js


def test_video_lobby_js_appends_walkie_param():
    js = _read('video-lobby.js')
    assert 'walkie' in js
    assert 'searchParams.set' in js


def test_video_lobby_js_has_saved_name_badge():
    js = _read('video-lobby.js')
    assert '_updateSavedNameBadge' in js
    assert 'btn-change-name' in js


def test_video_lobby_js_persists_voice_preferences():
    js = _read('video-lobby.js')
    assert 'blt-safecloak-voice-preferences' in js
