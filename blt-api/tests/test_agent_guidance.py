"""Regression tests for agent-focused development guidance."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = ROOT / "AGENTS.md"
CONTRIBUTING_MD = ROOT / "CONTRIBUTING.md"
INDEX_HTML = ROOT / "src" / "pages" / "index.html"
DASHBOARD_HTML = ROOT / "src" / "pages" / "dashboard.html"
HOMEPAGE_HANDLER = ROOT / "src" / "handlers" / "homepage.py"
AUTH_PAGE_HANDLER = ROOT / "src" / "handlers" / "auth_page.py"
DB_HELPER = ROOT / "src" / "libs" / "db.py"
API_KEY_HELPER = ROOT / "src" / "libs" / "api_key.py"


def _agents_text() -> str:
    return AGENTS_MD.read_text(encoding="utf-8")


def test_agents_md_exists_at_repo_root():
    assert AGENTS_MD.is_file()


def test_agents_md_covers_core_agent_context():
    text = _agents_text()
    lower_text = text.lower()

    for required in [
        "blt-api",
        "owasp blt",
        "src/main.py",
        "default.on_fetch",
        "src/router.py",
        "src/handlers/",
        "src/libs/api_key.py",
        "x-blt-api-key",
        "jwt",
        "bearer",
        "d1",
        "migrations/",
        "/v2",
        "tests/",
        "readme.md",
        "contributing.md",
        "docs/database.md",
    ]:
        assert required in lower_text


def test_agents_md_sets_safe_agent_guardrails():
    text = _agents_text().lower()

    assert "do not change" in text and "x-blt-api-key" in text
    assert "jwt" in text and "identity" in text
    assert "anonymous" in text and "out of scope" in text
    assert "secret" in text and ("do not commit" in text or "never commit" in text)
    assert "readme" in text and "human" in text


def test_agents_md_is_concise():
    non_empty_lines = [line for line in _agents_text().splitlines() if line.strip()]

    assert len(non_empty_lines) <= 140


def test_contributing_links_to_agents_md():
    text = CONTRIBUTING_MD.read_text(encoding="utf-8")

    assert "AGENTS.md" in text


def test_agents_md_maps_browser_pages_and_local_backups():
    text = _agents_text().lower()

    for required in [
        "get /",
        "src/pages/index.html",
        "get /dashboard",
        "src/pages/dashboard.html",
        "get /auth",
        "src/handlers/auth_page.py",
        "get /blt-api.svg",
        "static/blt-api.svg",
        "old-dashboard.html",
        "gitignored local backup",
    ]:
        assert required in text


def test_page_templates_have_route_micro_definitions():
    index_text = INDEX_HTML.read_text(encoding="utf-8")
    dashboard_text = DASHBOARD_HTML.read_text(encoding="utf-8")

    assert "GET /" in index_text
    assert "public landing page" in index_text
    assert "GET /dashboard" in dashboard_text
    assert "interactive API explorer" in dashboard_text


def test_route_page_handlers_have_micro_route_map():
    text = HOMEPAGE_HANDLER.read_text(encoding="utf-8")

    assert "GET / -> src/pages/index.html" in text
    assert "GET /dashboard -> src/pages/dashboard.html" in text
    assert "GET /blt-api.svg -> static/blt-api.svg" in text


def test_auth_page_handler_marks_browser_alias_not_json_api():
    text = AUTH_PAGE_HANDLER.read_text(encoding="utf-8")

    assert "Legacy browser /auth route" in text
    assert "not a JSON auth API endpoint" in text
    assert "/api/auth/*" in text


def test_core_helpers_define_api_gate_and_d1_binding():
    api_key_text = API_KEY_HELPER.read_text(encoding="utf-8")
    db_text = DB_HELPER.read_text(encoding="utf-8")

    assert "X-BLT-API-Key" in api_key_text
    assert "before router dispatch" in api_key_text
    assert "JWT/Bearer identity is separate" in api_key_text
    assert "Cloudflare D1 binding helpers" in db_text
    assert "blt_api" in db_text
    assert "wrangler.toml" in db_text
