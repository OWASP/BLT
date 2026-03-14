"""Admin service for BLT-Pool.

Keeps admin auth, session handling, and mentor management out of worker.py.
"""

import hashlib
import hmac
import html as _html
import json
import re
import secrets
import time
from typing import Optional
from urllib.parse import parse_qs, quote_plus, urlparse

from js import Headers, Response, console, fetch


_ADMIN_COOKIE = "blt_admin_session"
_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
_ADMIN_USERNAME_RE = r"^[A-Za-z0-9_.-]{3,32}$"
_INITIAL_MENTORS = [
    {"github_username": "rinkitadhana", "name": "Rinkit Adhana", "specialties": ["frontend", "javascript"], "max_mentees": 3, "active": True, "timezone": "UTC+5:30", "referred_by": ""},
    {"github_username": "Rajgupta36", "name": "Raj Gupta", "specialties": ["backend", "python"], "max_mentees": 3, "active": True, "timezone": "UTC+5:30", "referred_by": ""},
    {"github_username": "shriyashsoni", "name": "Shriyash Soni", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "Mohammedfaiyaz29", "name": "Mohammed Faiyaz Shaikh", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "Vaswani2003", "name": "Vinamra Vaswani", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "kittenbytes", "name": "Carla Voorhees", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "Captain-T2004", "name": "Akshay Behl", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "elsheik21", "name": "Ahmed ElSheik", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "Kunal1522", "name": "Kunal Kashyap", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "RudraBhaskar9439", "name": "Rudra Bhaskar", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "dev-sanidhya", "name": "Sanidhya Shishodia", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "VedantAnand17", "name": "Vedant Anand", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "Rishab87", "name": "Rishab Kumar Jha", "specialties": [], "max_mentees": 3, "active": True, "timezone": "", "referred_by": ""},
    {"github_username": "gitsofaryan", "name": "Aryan Jain", "specialties": ["fullstack", "web3", "distributed-systems", "ai-ml", "open-source", "devops", "realtime-systems"], "max_mentees": 3, "active": True, "timezone": "UTC+5:30 (India Standard Time)", "referred_by": ""},
    {"github_username": "ramansh18", "name": "Ramansh Saxena", "specialties": ["frontend", "backend", "web3"], "max_mentees": 2, "active": True, "timezone": "+5:30", "referred_by": "ojaswa072"},
]


def _escape(value: str) -> str:
    return _html.escape(value or "", quote=True)


def _cookie_value(cookie_header: str, name: str) -> str:
    if not cookie_header:
        return ""
    for item in cookie_header.split(";"):
        part = item.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key.strip() == name:
            return value.strip()
    return ""


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{salt.hex()}:{derived.hex()}"


def _password_matches(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, expected_hex = stored_hash.split(":", 1)
    except ValueError:
        return False
    recalculated = _password_hash(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(recalculated, stored_hash)


def _session_hash(session_token: str) -> str:
    return hashlib.sha256(session_token.encode("utf-8")).hexdigest()


def _github_headers(token: str = "") -> Headers:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BLT-Pool/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return Headers.new(headers.items())


async def has_merged_pr_in_org(env, github_username: str, org: str = "OWASP-BLT") -> bool:
    """Return True when the user has at least one merged PR in the org."""
    if not github_username:
        return False

    token = getattr(env, "GITHUB_TOKEN", "") if env else ""
    query = quote_plus(f"is:pr is:merged org:{org} author:{github_username}")
    url = f"https://api.github.com/search/issues?q={query}&per_page=1"

    try:
        resp = await fetch(url, method="GET", headers=_github_headers(token))
        if resp.status != 200:
            console.error(
                f"[AdminService] Merged PR lookup failed for {github_username}: status={resp.status}"
            )
            return False
        payload = json.loads(await resp.text())
        return int(payload.get("total_count") or 0) > 0
    except Exception as exc:
        console.error(f"[AdminService] Merged PR lookup error for {github_username}: {exc}")
        return False


class AdminService:
    """D1-backed admin auth and mentor management UI."""

    def __init__(self, env):
        self.env = env
        self.db = getattr(env, "LEADERBOARD_DB", None) if env else None

    async def handle(self, request):
        """Handle admin routes, or return None when the path is not for this service."""
        path = urlparse(str(request.url)).path.rstrip("/") or "/"
        if path == "/admin/reset-leaderboard-month":
            return None
        if not path.startswith("/admin"):
            return None
        if not self.db:
            return self._html(
                self._shell(
                    "Admin unavailable",
                    "<p class='text-sm text-gray-600'>The D1 database binding is not configured.</p>",
                ),
                500,
            )

        await self._ensure_tables()

        if path == "/admin/signup":
            if request.method == "POST":
                return await self._handle_signup_post(request)
            return await self._handle_signup_get(request)

        if path == "/admin/login":
            if request.method == "POST":
                return await self._handle_login_post(request)
            return await self._handle_login_get(request)

        if path == "/admin/logout":
            return await self._handle_logout(request)

        if path == "/admin/mentors/action" and request.method == "POST":
            return await self._handle_mentor_action(request)

        if path == "/admin":
            return await self._handle_dashboard(request)

        return self._json({"error": "Not found"}, 404)

    async def _d1_run(self, sql: str, params: tuple = ()):
        stmt = self.db.prepare(sql)
        if params:
            stmt = stmt.bind(*params)
        return await stmt.run()

    async def _d1_all(self, sql: str, params: tuple = ()) -> list:
        stmt = self.db.prepare(sql)
        if params:
            stmt = stmt.bind(*params)
        raw_result = await stmt.all()

        try:
            from js import JSON as JS_JSON  # noqa: PLC0415

            parsed = json.loads(str(JS_JSON.stringify(raw_result)))
            rows = parsed.get("results") if isinstance(parsed, dict) else None
            if isinstance(rows, list):
                return rows
        except Exception:
            pass

        try:
            from pyodide.ffi import to_py  # noqa: PLC0415

            result = to_py(raw_result)
        except Exception:
            result = raw_result

        rows = None
        if isinstance(result, dict):
            rows = result.get("results")
        else:
            rows = getattr(result, "results", None)

        if rows is None:
            return []
        try:
            return list(rows)
        except Exception:
            return []

    async def _d1_first(self, sql: str, params: tuple = ()):
        rows = await self._d1_all(sql, params)
        return rows[0] if rows else None

    async def _ensure_tables(self) -> None:
        await self._d1_run(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        await self._d1_run(
            """
            CREATE TABLE IF NOT EXISTS admin_sessions (
                session_hash TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """
        )
        await self._d1_run(
            """
            CREATE TABLE IF NOT EXISTS mentors (
                github_username TEXT NOT NULL PRIMARY KEY,
                name TEXT NOT NULL,
                specialties TEXT NOT NULL DEFAULT '[]',
                max_mentees INTEGER NOT NULL DEFAULT 3,
                active INTEGER NOT NULL DEFAULT 1,
                timezone TEXT NOT NULL DEFAULT '',
                referred_by TEXT NOT NULL DEFAULT ''
            )
            """
        )
        await self._d1_run(
            """
            CREATE TABLE IF NOT EXISTS mentor_assignments (
                org TEXT NOT NULL,
                mentor_login TEXT NOT NULL,
                issue_repo TEXT NOT NULL,
                issue_number INTEGER NOT NULL,
                assigned_at INTEGER NOT NULL,
                PRIMARY KEY (org, issue_repo, issue_number)
            )
            """
        )
        await self._d1_run(
            "DELETE FROM admin_sessions WHERE expires_at <= ?",
            (int(time.time()),),
        )
        await self._seed_mentors()

    async def _seed_mentors(self) -> None:
        for mentor in _INITIAL_MENTORS:
            await self._d1_run(
                """
                INSERT OR IGNORE INTO mentors
                    (github_username, name, specialties, max_mentees, active, timezone, referred_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mentor["github_username"],
                    mentor["name"],
                    json.dumps(mentor.get("specialties") or []),
                    mentor.get("max_mentees", 3),
                    1 if mentor.get("active", True) else 0,
                    mentor.get("timezone", ""),
                    mentor.get("referred_by", ""),
                ),
            )

    async def _has_admin(self) -> bool:
        row = await self._d1_first("SELECT username FROM admin_users WHERE id = 1")
        return bool(row and row.get("username"))

    async def _current_admin(self, request) -> Optional[str]:
        cookie = _cookie_value(request.headers.get("Cookie") or "", _ADMIN_COOKIE)
        if not cookie:
            return None
        hashed = _session_hash(cookie)
        row = await self._d1_first(
            "SELECT username, expires_at FROM admin_sessions WHERE session_hash = ?",
            (hashed,),
        )
        if not row:
            return None
        if int(row.get("expires_at") or 0) <= int(time.time()):
            await self._d1_run("DELETE FROM admin_sessions WHERE session_hash = ?", (hashed,))
            return None
        return row.get("username")

    async def _create_session(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        await self._d1_run(
            """
            INSERT INTO admin_sessions (session_hash, username, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (_session_hash(token), username, now, now + _SESSION_TTL_SECONDS),
        )
        return token

    async def _delete_session(self, request) -> None:
        cookie = _cookie_value(request.headers.get("Cookie") or "", _ADMIN_COOKIE)
        if cookie:
            await self._d1_run(
                "DELETE FROM admin_sessions WHERE session_hash = ?",
                (_session_hash(cookie),),
            )

    async def _form_data(self, request) -> dict:
        body = await request.text()
        parsed = parse_qs(body, keep_blank_values=False)
        return {key: values[0].strip() if values else "" for key, values in parsed.items()}

    def _json(self, payload, status: int = 200):
        return Response.new(
            json.dumps(payload),
            status=status,
            headers=Headers.new({"Content-Type": "application/json"}.items()),
        )

    def _html(self, body: str, status: int = 200, set_cookie: str = ""):
        headers = {"Content-Type": "text/html; charset=utf-8"}
        if set_cookie:
            headers["Set-Cookie"] = set_cookie
        return Response.new(body, status=status, headers=Headers.new(headers.items()))

    def _redirect(self, location: str, set_cookie: str = ""):
        headers = {"Location": location}
        if set_cookie:
            headers["Set-Cookie"] = set_cookie
        return Response.new("", status=302, headers=Headers.new(headers.items()))

    def _session_cookie(self, token: str) -> str:
        return (
            f"{_ADMIN_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; "
            f"Max-Age={_SESSION_TTL_SECONDS}"
        )

    def _clear_session_cookie(self) -> str:
        return f"{_ADMIN_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"

    def _shell(self, title: str, content: str, user: str = "", subtitle: str = "") -> str:
        user_chip = ""
        if user:
            user_chip = (
                f'<div class="inline-flex items-center gap-2 rounded-full border border-[#E5E5E5] '
                f'bg-white px-3 py-1 text-xs font-semibold text-gray-600">Signed in as @{_escape(user)}</div>'
            )
        subtitle_html = f"<p class='mt-3 text-sm leading-relaxed text-gray-600'>{subtitle}</p>" if subtitle else ""
        return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_escape(title)} | BLT-Pool Admin</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" crossorigin="anonymous" referrerpolicy="no-referrer">
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            'blt-primary': '#E10101',
            'blt-border': '#E5E5E5'
          }},
          fontFamily: {{
            sans: ['Plus Jakarta Sans', 'ui-sans-serif', 'system-ui', 'sans-serif']
          }}
        }}
      }}
    }}
  </script>
  <style>
    body {{
      background:
        radial-gradient(circle at 0% 0%, rgba(225, 1, 1, 0.09), transparent 32%),
        radial-gradient(circle at 95% 4%, rgba(225, 1, 1, 0.05), transparent 28%),
        #f8fafc;
    }}
  </style>
</head>
<body class="min-h-screen font-sans text-gray-900 antialiased">
  <header class="sticky top-0 z-40 border-b border-[#E5E5E5] bg-white/90 backdrop-blur">
    <div class="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-4 sm:px-6 lg:px-8">
      <a href="/admin" class="flex items-center gap-3" aria-label="BLT-Pool admin home">
        <img src="/logo-sm.png" alt="OWASP BLT logo" class="h-10 w-10 rounded-xl border border-[#E5E5E5] bg-white object-contain p-1">
        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-gray-500">OWASP BLT</p>
          <h1 class="text-lg font-extrabold text-[#111827]">BLT-Pool Admin</h1>
        </div>
      </a>
      <div class="flex items-center gap-3">
        {user_chip}
        {"<a href='/admin/logout' class='inline-flex items-center gap-2 rounded-md border border-[#E10101] px-4 py-2 text-sm font-semibold text-[#E10101] transition hover:bg-[#E10101] hover:text-white'><i class='fa-solid fa-right-from-bracket' aria-hidden='true'></i>Logout</a>" if user else ""}
      </div>
    </div>
  </header>
  <main class="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
    <section class="overflow-hidden rounded-3xl border border-[#E5E5E5] bg-white p-7 shadow-[0_14px_40px_rgba(225,1,1,0.10)] sm:p-10">
      <div class="mb-8">
        <span class="inline-flex items-center gap-2 rounded-full border border-[#E5E5E5] bg-gray-50 px-3 py-1 text-xs font-semibold text-gray-700">
          <i class="fa-solid fa-shield-halved text-[#E10101]" aria-hidden="true"></i>
          Admin access
        </span>
        <h2 class="mt-4 text-3xl font-extrabold text-[#111827] sm:text-4xl">{_escape(title)}</h2>
        {subtitle_html}
      </div>
      {content}
    </section>
  </main>
</body>
</html>"""

    def _auth_form(self, mode: str, error: str = "") -> str:
        title = "Create the first admin" if mode == "signup" else "Admin login"
        action = "/admin/signup" if mode == "signup" else "/admin/login"
        submit = "Create admin" if mode == "signup" else "Login"
        helper = (
            "This route only works once. After the first admin is created, future visits go through login."
            if mode == "signup"
            else "Use the admin account created during first-time setup."
        )
        confirm_field = ""
        if mode == "signup":
            confirm_field = """
            <div>
              <label for="confirm_password" class="mb-1 block text-sm font-semibold text-gray-700">Confirm password</label>
              <input id="confirm_password" name="confirm_password" type="password" required class="w-full rounded-md border border-gray-400 px-4 py-2 text-sm text-gray-900 focus:border-red-600 focus:ring-1 focus:ring-red-600 focus:outline-none">
            </div>
            """
        error_html = ""
        if error:
            error_html = f"<p class='mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700'>{_escape(error)}</p>"
        content = f"""
        <div class="mx-auto max-w-md">
          <p class="mb-6 text-sm leading-relaxed text-gray-600">{helper}</p>
          {error_html}
          <form method="POST" action="{action}" class="space-y-4">
            <div>
              <label for="username" class="mb-1 block text-sm font-semibold text-gray-700">Username</label>
              <input id="username" name="username" type="text" autocomplete="username" required class="w-full rounded-md border border-gray-400 px-4 py-2 text-sm text-gray-900 focus:border-red-600 focus:ring-1 focus:ring-red-600 focus:outline-none">
            </div>
            <div>
              <label for="password" class="mb-1 block text-sm font-semibold text-gray-700">Password</label>
              <input id="password" name="password" type="password" autocomplete="current-password" required class="w-full rounded-md border border-gray-400 px-4 py-2 text-sm text-gray-900 focus:border-red-600 focus:ring-1 focus:ring-red-600 focus:outline-none">
            </div>
            {confirm_field}
            <button type="submit" class="inline-flex items-center gap-2 rounded-md bg-[#E10101] px-5 py-3 text-sm font-semibold text-white transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2">
              <i class="fa-solid fa-lock" aria-hidden="true"></i>
              {submit}
            </button>
          </form>
        </div>
        """
        return self._shell(title, content, subtitle="Simple D1-backed admin auth for mentor management.")

    async def _handle_signup_get(self, request):
        if await self._has_admin():
            current = await self._current_admin(request)
            if current:
                return self._redirect("/admin")
            return self._redirect("/admin/login")
        return self._html(self._auth_form("signup"))

    async def _handle_signup_post(self, request):
        if await self._has_admin():
            return self._redirect("/admin/login")

        form = await self._form_data(request)
        username = form.get("username", "")
        password = form.get("password", "")
        confirm = form.get("confirm_password", "")

        if not username or not password:
            return self._html(self._auth_form("signup", "Username and password are required."), 400)
        if not re.match(_ADMIN_USERNAME_RE, username):
            return self._html(self._auth_form("signup", "Username must be 3-32 characters using letters, numbers, dot, underscore, or hyphen."), 400)
        if len(password) < 8:
            return self._html(self._auth_form("signup", "Password must be at least 8 characters."), 400)
        if password != confirm:
            return self._html(self._auth_form("signup", "Passwords do not match."), 400)

        try:
            await self._d1_run(
                "INSERT INTO admin_users (id, username, password_hash, created_at) VALUES (1, ?, ?, ?)",
                (username, _password_hash(password), int(time.time())),
            )
        except Exception as exc:
            console.error(f"[AdminService] Failed to create first admin: {exc}")
            return self._html(self._auth_form("signup", "Admin setup is already complete or the account could not be created."), 409)

        token = await self._create_session(username)
        return self._redirect("/admin", set_cookie=self._session_cookie(token))

    async def _handle_login_get(self, request):
        if not await self._has_admin():
            return self._redirect("/admin/signup")
        current = await self._current_admin(request)
        if current:
            return self._redirect("/admin")
        return self._html(self._auth_form("login"))

    async def _handle_login_post(self, request):
        if not await self._has_admin():
            return self._redirect("/admin/signup")

        form = await self._form_data(request)
        username = form.get("username", "")
        password = form.get("password", "")
        row = await self._d1_first("SELECT username, password_hash FROM admin_users WHERE id = 1")
        if not row or row.get("username") != username or not _password_matches(password, row.get("password_hash", "")):
            return self._html(self._auth_form("login", "Invalid username or password."), 401)

        token = await self._create_session(username)
        return self._redirect("/admin", set_cookie=self._session_cookie(token))

    async def _handle_logout(self, request):
        await self._delete_session(request)
        return self._redirect("/admin/login", set_cookie=self._clear_session_cookie())

    async def _handle_dashboard(self, request):
        if not await self._has_admin():
            return self._redirect("/admin/signup")
        username = await self._current_admin(request)
        if not username:
            return self._redirect("/admin/login")

        mentors = await self._mentor_rows()
        counts = {
            "total": len(mentors),
            "active": len([m for m in mentors if int(m.get("active") or 0) == 1]),
            "inactive": len([m for m in mentors if int(m.get("active") or 0) != 1]),
            "assignments": sum(int(m.get("assignment_count") or 0) for m in mentors),
        }

        mentor_rows = "\n".join(self._mentor_row_html(row) for row in mentors)
        if not mentor_rows:
            mentor_rows = (
                "<tr><td colspan='8' class='px-4 py-6 text-center text-sm text-gray-500'>"
                "No mentors found in D1 yet.</td></tr>"
            )

        content = f"""
        <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Total mentors</p>
            <p class="mt-1 text-2xl font-extrabold text-[#111827]">{counts['total']}</p>
          </article>
          <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Published</p>
            <p class="mt-1 text-2xl font-extrabold text-[#111827]">{counts['active']}</p>
          </article>
          <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Blocked / pending</p>
            <p class="mt-1 text-2xl font-extrabold text-[#111827]">{counts['inactive']}</p>
          </article>
          <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Active assignments</p>
            <p class="mt-1 text-2xl font-extrabold text-[#111827]">{counts['assignments']}</p>
          </article>
        </div>

        <div class="mt-8 rounded-2xl border border-[#E5E5E5] bg-white">
          <div class="border-b border-[#E5E5E5] px-5 py-4">
            <h3 class="text-lg font-bold text-[#111827]">Mentor management</h3>
            <p class="mt-1 text-sm text-gray-600">Publish, block, or delete mentors from the pool.</p>
          </div>
          <div class="overflow-x-auto">
            <table class="min-w-full text-left text-sm">
              <thead class="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <tr>
                  <th class="px-4 py-3">Mentor</th>
                  <th class="px-4 py-3">Status</th>
                  <th class="px-4 py-3">Specialties</th>
                  <th class="px-4 py-3">Cap</th>
                  <th class="px-4 py-3">Timezone</th>
                  <th class="px-4 py-3">Referral</th>
                  <th class="px-4 py-3">Assignments</th>
                  <th class="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[#E5E5E5]">
                {mentor_rows}
              </tbody>
            </table>
          </div>
        </div>
        """
        return self._html(
            self._shell(
                "Admin dashboard",
                content,
                user=username,
                subtitle="Manage mentor publishing and keep the public mentor pool healthy.",
            )
        )

    async def _mentor_rows(self) -> list:
        rows = await self._d1_all(
            """
            SELECT
                m.github_username,
                m.name,
                m.specialties,
                m.max_mentees,
                m.active,
                m.timezone,
                m.referred_by,
                COALESCE(a.assignment_count, 0) AS assignment_count
            FROM mentors m
            LEFT JOIN (
                SELECT mentor_login, COUNT(*) AS assignment_count
                FROM mentor_assignments
                GROUP BY mentor_login
            ) a
            ON a.mentor_login = m.github_username
            ORDER BY m.active DESC, LOWER(m.name) ASC
            """
        )
        parsed = []
        for row in rows:
            try:
                specialties = json.loads(row.get("specialties") or "[]")
            except Exception:
                specialties = []
            parsed.append({**row, "specialties_list": specialties})
        return parsed

    def _mentor_row_html(self, mentor: dict) -> str:
        username = mentor.get("github_username", "")
        name = mentor.get("name", "")
        active = int(mentor.get("active") or 0) == 1
        specialties = mentor.get("specialties_list") or []
        specialty_html = " ".join(
            f'<span class="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">{_escape(str(item))}</span>'
            for item in specialties
        ) or '<span class="text-xs text-gray-400">-</span>'
        badge = (
            '<span class="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">Published</span>'
            if active
            else '<span class="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs font-semibold text-gray-600">Blocked</span>'
        )
        primary_action = "block" if active else "publish"
        primary_label = "Block" if active else "Publish"
        primary_class = (
            "border-gray-300 text-gray-700 hover:bg-gray-50"
            if active
            else "border-emerald-200 text-emerald-700 hover:bg-emerald-50"
        )
        return f"""
        <tr>
          <td class="px-4 py-4">
            <div class="flex items-center gap-3">
              <img src="https://github.com/{_escape(username)}.png" alt="{_escape(name)}" class="h-9 w-9 rounded-full border border-[#E5E5E5] bg-white object-cover">
              <div>
                <p class="font-semibold text-[#111827]">{_escape(name)}</p>
                <a href="https://github.com/{_escape(username)}" target="_blank" rel="noopener" class="text-xs text-red-600 hover:underline">@{_escape(username)}</a>
              </div>
            </div>
          </td>
          <td class="px-4 py-4">{badge}</td>
          <td class="px-4 py-4"><div class="flex flex-wrap gap-1">{specialty_html}</div></td>
          <td class="px-4 py-4 text-gray-600">{int(mentor.get('max_mentees') or 3)}</td>
          <td class="px-4 py-4 text-gray-600">{_escape(mentor.get('timezone') or '-')}</td>
          <td class="px-4 py-4 text-gray-600">{_escape(mentor.get('referred_by') or '-')}</td>
          <td class="px-4 py-4 text-gray-600">{int(mentor.get('assignment_count') or 0)}</td>
          <td class="px-4 py-4">
            <div class="flex flex-wrap gap-2">
              <form method="POST" action="/admin/mentors/action">
                <input type="hidden" name="github_username" value="{_escape(username)}">
                <input type="hidden" name="action" value="{primary_action}">
                <button type="submit" class="inline-flex items-center gap-1 rounded-md border px-3 py-2 text-xs font-semibold transition {primary_class}">
                  {primary_label}
                </button>
              </form>
              <form method="POST" action="/admin/mentors/action">
                <input type="hidden" name="github_username" value="{_escape(username)}">
                <input type="hidden" name="action" value="delete">
                <button type="submit" class="inline-flex items-center gap-1 rounded-md border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 transition hover:bg-red-50">
                  Delete
                </button>
              </form>
            </div>
          </td>
        </tr>
        """

    async def _handle_mentor_action(self, request):
        if not await self._current_admin(request):
            return self._redirect("/admin/login")

        form = await self._form_data(request)
        github_username = (form.get("github_username") or "").strip().lstrip("@")
        action = (form.get("action") or "").strip().lower()
        if not github_username or action not in {"publish", "block", "delete"}:
            return self._redirect("/admin")

        try:
            if action == "publish":
                await self._d1_run("UPDATE mentors SET active = 1 WHERE github_username = ?", (github_username,))
            elif action == "block":
                await self._d1_run("UPDATE mentors SET active = 0 WHERE github_username = ?", (github_username,))
            else:
                await self._d1_run("DELETE FROM mentor_assignments WHERE mentor_login = ?", (github_username,))
                await self._d1_run("DELETE FROM mentors WHERE github_username = ?", (github_username,))
        except Exception as exc:
            console.error(f"[AdminService] Mentor action '{action}' failed for {github_username}: {exc}")
        return self._redirect("/admin")
