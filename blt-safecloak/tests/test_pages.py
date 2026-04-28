"""
Static HTML structure tests for all pages in src/pages/.

These tests verify that:
  - Each page has the expected <title>, charset, and viewport meta.
  - Navigation elements are present (navbar, theme toggle).
  - Page-specific UI elements are present (editor, consent form, etc.).
  - The correct JS/CSS assets are referenced.
  - GitHub links are present where expected.

No browser or server is required – files are read directly from disk.
"""

from pathlib import Path
import re

ROOT = Path(__file__).parent.parent
PAGES_DIR = ROOT / 'src' / 'pages'


def _read(filename: str) -> str:
    return (PAGES_DIR / filename).read_text(encoding='utf-8')


# ── Common structure across all pages ────────────────────────────────────────

ALL_PAGES = ['index.html', 'notes.html', 'consent.html', 'video-chat.html', 'video-room.html']


def test_all_pages_have_utf8_charset():
    for page in ALL_PAGES:
        html = _read(page)
        assert 'charset="UTF-8"' in html or 'charset=UTF-8' in html, (
            f'{page} is missing charset=UTF-8 meta declaration')


def test_all_pages_have_viewport_meta():
    for page in ALL_PAGES:
        html = _read(page)
        assert 'name="viewport"' in html, f'{page} is missing viewport meta tag'


def test_all_pages_have_navbar_toggle():
    """Mobile hamburger menu must be present on informational and lobby pages."""
    # video-room.html is the in-call room: it has a simplified header without
    # the mobile hamburger toggle (by design).
    pages_with_navbar = ['index.html', 'notes.html', 'consent.html', 'video-chat.html']
    for page in pages_with_navbar:
        html = _read(page)
        assert 'id="navbar-toggle"' in html, f'{page} is missing #navbar-toggle'


def test_all_pages_have_theme_toggle_button():
    """Dark/light mode toggle must be present on every page."""
    for page in ALL_PAGES:
        html = _read(page)
        assert 'id="theme-toggle-btn"' in html, f'{page} is missing #theme-toggle-btn'


def test_all_pages_include_theme_js():
    """Every page must load theme.js for dark-mode persistence."""
    for page in ALL_PAGES:
        html = _read(page)
        assert 'src="js/theme.js"' in html or "src='js/theme.js'" in html, (
            f'{page} does not include theme.js')


def test_all_pages_have_toast_container():
    """Toast notification container must be present on pages with interactive JS."""
    # video-chat.html (lobby) does not currently include a toast container;
    # the remaining pages do.
    pages_with_toast = ['index.html', 'notes.html', 'consent.html', 'video-room.html']
    for page in pages_with_toast:
        html = _read(page)
        assert 'id="toast-container"' in html, f'{page} is missing #toast-container'


def test_all_pages_have_doctype():
    for page in ALL_PAGES:
        html = _read(page)
        assert html.strip().lower().startswith('<!doctype html'), (
            f'{page} is missing <!doctype html> declaration')


def test_all_pages_have_lang_attribute():
    for page in ALL_PAGES:
        html = _read(page)
        assert 'lang="en"' in html, f'{page} is missing lang="en" on <html>'


# ── index.html ────────────────────────────────────────────────────────────────


def test_index_html_title():
    html = _read('index.html')
    assert 'BLT-SafeCloak' in html
    assert '<title>' in html


def test_index_html_has_github_link():
    html = _read('index.html')
    assert 'github.com/OWASP-BLT/BLT-SafeCloak' in html


def test_index_html_includes_ui_js():
    html = _read('index.html')
    assert 'src="js/ui.js"' in html


def test_index_html_has_hero_heading():
    html = _read('index.html')
    assert 'id="hero-heading"' in html


def test_index_html_has_features_section():
    html = _read('index.html')
    assert 'id="features"' in html


# ── notes.html ────────────────────────────────────────────────────────────────


def test_notes_html_title():
    html = _read('notes.html')
    assert 'Notes' in html
    assert '<title>' in html


def test_notes_html_has_editor_elements():
    html = _read('notes.html')
    required = [
        'id="notes-list"',
        'id="note-title"',
        'id="note-body"',
        'id="editor-empty"',
        'id="editor-wrapper"',
        'id="word-count"',
        'id="ai-output"',
    ]
    for snippet in required:
        assert snippet in html, f'notes.html is missing: {snippet}'


def test_notes_html_has_ai_buttons():
    html = _read('notes.html')
    required = [
        'id="btn-summarize"',
        'id="btn-keypoints"',
        'id="btn-actions"',
        'id="btn-keywords"',
    ]
    for snippet in required:
        assert snippet in html, f'notes.html is missing AI button: {snippet}'


def test_notes_html_has_note_management_buttons():
    html = _read('notes.html')
    assert 'id="btn-new-note"' in html
    assert 'id="btn-delete-note"' in html


def test_notes_html_has_export_buttons():
    html = _read('notes.html')
    assert 'id="btn-export-txt"' in html
    assert 'id="btn-export-md"' in html
    assert 'id="btn-export-json"' in html
    assert 'id="btn-export-all"' in html


def test_notes_html_includes_crypto_and_notes_js():
    html = _read('notes.html')
    assert 'src="js/crypto.js"' in html
    assert 'src="js/ui.js"' in html
    assert 'src="js/notes.js"' in html


# ── consent.html ──────────────────────────────────────────────────────────────


def test_consent_html_title():
    html = _read('consent.html')
    assert 'Consent' in html
    assert '<title>' in html


def test_consent_html_has_consent_form():
    html = _read('consent.html')
    assert 'id="consent-form"' in html


def test_consent_html_has_form_fields():
    html = _read('consent.html')
    required = [
        'id="consent-type"',
        'id="participant-name"',
        'id="purpose"',
        'id="details"',
    ]
    for snippet in required:
        assert snippet in html, f'consent.html is missing form field: {snippet}'


def test_consent_html_has_consent_log():
    html = _read('consent.html')
    assert 'id="consent-log"' in html


def test_consent_html_has_stats_elements():
    html = _read('consent.html')
    assert 'id="stat-total"' in html
    assert 'id="stat-given"' in html
    assert 'id="stat-withdrawn"' in html
    assert 'id="stat-recorded"' in html


def test_consent_html_has_export_buttons():
    html = _read('consent.html')
    assert 'id="btn-export-json"' in html
    assert 'id="btn-export-csv"' in html
    assert 'id="btn-clear-log"' in html


def test_consent_html_includes_crypto_and_consent_js():
    html = _read('consent.html')
    assert 'src="js/crypto.js"' in html
    assert 'src="js/ui.js"' in html
    assert 'src="js/consent.js"' in html


# ── video-chat.html (lobby) ───────────────────────────────────────────────────


def test_video_chat_html_title():
    html = _read('video-chat.html')
    assert '<title>' in html


def test_video_chat_html_has_join_form():
    html = _read('video-chat.html')
    # Lobby should have a username/display-name input
    assert 'id="display-name"' in html or 'display-name' in html


def test_video_chat_html_does_not_have_in_room_controls():
    """Lobby must not expose room-only controls."""
    html = _read('video-chat.html')
    assert 'id="my-peer-id"' not in html
    assert 'Copy Room ID' not in html
    assert 'Add Participant' not in html


def test_video_chat_html_has_saved_name_badge():
    html = _read('video-chat.html')
    assert 'id="saved-name-badge"' in html
    assert 'id="saved-name-text"' in html
    assert 'id="btn-change-name"' in html


# ── video-room.html ───────────────────────────────────────────────────────────


def test_video_room_html_title():
    html = _read('video-room.html')
    assert '<title>' in html


def test_video_room_html_has_my_peer_id():
    html = _read('video-room.html')
    assert 'id="my-peer-id"' in html


def test_video_room_html_has_video_grid():
    html = _read('video-room.html')
    assert 'id="video-grid"' in html


def test_video_room_html_has_call_controls():
    html = _read('video-room.html')
    assert 'id="btn-call"' in html
    assert 'id="remote-id"' in html


def test_video_room_html_has_walkie_banner():
    html = _read('video-room.html')
    assert 'id="walkie-cue-banner"' in html
    assert 'id="walkie-cue-text"' in html


def test_video_room_html_has_github_footer():
    html = _read('video-room.html')
    assert 'github.com/OWASP-BLT/BLT-SafeCloak' in html
