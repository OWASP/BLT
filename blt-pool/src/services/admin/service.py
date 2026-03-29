"""Admin service for BLT-Pool.

Keeps admin auth and mentor management out of worker.py.
"""

import base64
import binascii
import hmac
import html as _html
import json
import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, quote_plus, urlparse

from js import Headers, Response, console, fetch


_ADMIN_BASIC_USER_ENV = "ADMIN_BASIC_AUTH_USERNAME"
_ADMIN_BASIC_PASS_ENV = "ADMIN_BASIC_AUTH_PASSWORD"
_ADMIN_BASIC_REALM = "BLT-Pool Admin"
_GH_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?$")
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,190}\.[A-Za-z]{2,}$")
_SLACK_USERNAME_RE = re.compile(r"^[A-Za-z0-9._\-]{1,80}$")


def _escape(value: str) -> str:
    return _html.escape(value or "", quote=True)


def _normalize_admin_path(raw_path: str) -> str:
    value = (raw_path or "").strip()
    if not value:
        return "/admin"
    if not value.startswith("/"):
        value = "/" + value
    value = value.rstrip("/")
    return value or "/admin"


def _parse_basic_auth_header(auth_header: str) -> Tuple[str, str]:
    """Parse a Basic auth header and return (username, password)."""
    if not auth_header:
        return "", ""
    prefix = "Basic "
    if not auth_header.startswith(prefix):
        return "", ""

    encoded = auth_header[len(prefix):].strip()
    if not encoded:
        return "", ""

    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return "", ""

    if ":" not in decoded:
        return "", ""

    username, password = decoded.split(":", 1)
    return username, password


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
        self.admin_path = _normalize_admin_path(getattr(env, "ADMIN_PATH", "/admin") if env else "/admin")
        self.mentor_action_path = f"{self.admin_path}/mentors/action"

    async def handle(self, request):
        """Handle admin routes, or return None when the path is not for this service."""
        path = urlparse(str(request.url)).path.rstrip("/") or "/"

        # Reset endpoint is handled in worker.py.
        if path in {"/admin/reset-leaderboard-month", f"{self.admin_path}/reset-leaderboard-month"}:
            return None

        if not (path == self.admin_path or path.startswith(f"{self.admin_path}/")):
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

        if path in {
            f"{self.admin_path}/login",
            f"{self.admin_path}/signup",
            f"{self.admin_path}/logout",
        }:
            return self._redirect(self.admin_path)

        configured_user, configured_pass = self._configured_basic_auth()
        if not configured_user or not configured_pass:
            return self._html(
                self._shell(
                    "Admin unavailable",
                    "<p class='text-sm text-gray-600'>"
                    f"Set {_ADMIN_BASIC_USER_ENV} and {_ADMIN_BASIC_PASS_ENV} "
                    f"to enable Basic Auth for {self.admin_path}.</p>",
                ),
                500,
            )

        request_user = self._authorized_admin(request, configured_user, configured_pass)
        if not request_user:
            return self._basic_auth_challenge()

        if path == self.mentor_action_path and request.method == "POST":
            return await self._handle_mentor_action(request, request_user)

        if path == self.admin_path:
            return await self._handle_dashboard(request_user)

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
            CREATE TABLE IF NOT EXISTS mentors (
                github_username TEXT NOT NULL PRIMARY KEY,
                name TEXT NOT NULL,
                specialties TEXT NOT NULL DEFAULT '[]',
                max_mentees INTEGER NOT NULL DEFAULT 3,
                active INTEGER NOT NULL DEFAULT 1,
                timezone TEXT NOT NULL DEFAULT '',
            referred_by TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            slack_username TEXT NOT NULL DEFAULT ''
            )
            """
        )
        if not await self._d1_has_column("mentors", "email"):
          await self._d1_run(
            "ALTER TABLE mentors ADD COLUMN email TEXT NOT NULL DEFAULT ''"
          )
        if not await self._d1_has_column("mentors", "slack_username"):
          await self._d1_run(
            "ALTER TABLE mentors ADD COLUMN slack_username TEXT NOT NULL DEFAULT ''"
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

        async def _d1_has_column(self, table_name: str, column_name: str) -> bool:
          rows = await self._d1_all(f"PRAGMA table_info({table_name})")
          target = (column_name or "").strip().lower()
          for row in rows:
            if str(row.get("name") or "").strip().lower() == target:
              return True
          return False

    def _configured_basic_auth(self) -> Tuple[str, str]:
        username = str(getattr(self.env, _ADMIN_BASIC_USER_ENV, "") or "").strip()
        password = str(getattr(self.env, _ADMIN_BASIC_PASS_ENV, "") or "")
        return username, password

    def _authorized_admin(self, request, expected_user: str, expected_pass: str) -> Optional[str]:
        supplied_user, supplied_pass = _parse_basic_auth_header(request.headers.get("Authorization") or "")
        if not supplied_user and not supplied_pass:
            return None
        if not hmac.compare_digest(supplied_user, expected_user):
            return None
        if not hmac.compare_digest(supplied_pass, expected_pass):
            return None
        return supplied_user

    def _basic_auth_challenge(self):
        return Response.new(
            "Authentication required",
            status=401,
            headers=Headers.new(
                {
                    "Content-Type": "text/plain; charset=utf-8",
                    "WWW-Authenticate": f'Basic realm="{_ADMIN_BASIC_REALM}", charset="UTF-8"',
                }.items()
            ),
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

    def _html(self, body: str, status: int = 200):
        headers = {"Content-Type": "text/html; charset=utf-8"}
        return Response.new(body, status=status, headers=Headers.new(headers.items()))

    def _redirect(self, location: str):
        headers = {"Location": location}
        return Response.new("", status=302, headers=Headers.new(headers.items()))

    def _shell(self, title: str, content: str, user: str = "", subtitle: str = "") -> str:
        auth_chip = (
            f'<div class="inline-flex items-center gap-2 rounded-full border border-[#E5E5E5] '
            f'bg-white px-3 py-1 text-xs font-semibold text-gray-600">Basic Auth as @{_escape(user)}</div>'
            if user
            else ""
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
      <a href="{self.admin_path}" class="flex items-center gap-3" aria-label="BLT-Pool admin home">
        <img src="/logo-sm.png" alt="OWASP BLT logo" class="h-10 w-10 rounded-xl border border-[#E5E5E5] bg-white object-contain p-1">
        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-gray-500">OWASP BLT</p>
          <h1 class="text-lg font-extrabold text-[#111827]">BLT-Pool Admin</h1>
        </div>
      </a>
      <div class="flex items-center gap-3">
        {auth_chip}
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
  <div id="admin-confirm-overlay" class="fixed inset-0 z-50 hidden items-center justify-center bg-[#111827]/45 px-4 backdrop-blur-sm" aria-hidden="true">
    <div class="w-full max-w-md overflow-hidden rounded-3xl border border-[#E5E5E5] bg-white shadow-[0_24px_80px_rgba(17,24,39,0.20)]">
      <div class="border-b border-[#E5E5E5] bg-gradient-to-r from-[#fff5f5] via-white to-[#fff1f1] px-6 py-5">
        <div class="flex items-start gap-4">
          <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#feeae9] text-[#E10101]">
            <i class="fa-solid fa-triangle-exclamation text-lg" aria-hidden="true"></i>
          </div>
          <div class="min-w-0">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Please confirm</p>
            <h3 id="admin-confirm-title" class="mt-1 text-xl font-extrabold text-[#111827]">Confirm action</h3>
          </div>
        </div>
      </div>
      <div class="px-6 py-5">
        <p id="admin-confirm-message" class="text-sm leading-relaxed text-gray-600">This action will update the mentor record.</p>
      </div>
      <div class="flex flex-col-reverse gap-3 border-t border-[#E5E5E5] bg-gray-50 px-6 py-4 sm:flex-row sm:justify-end">
        <button id="admin-confirm-cancel" type="button" class="inline-flex items-center justify-center rounded-md border border-[#E5E5E5] px-4 py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-white">
          Cancel
        </button>
        <button id="admin-confirm-submit" type="button" class="inline-flex items-center justify-center gap-2 rounded-md bg-[#E10101] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-700">
          <i class="fa-solid fa-check" aria-hidden="true"></i>
          Continue
        </button>
      </div>
    </div>
  </div>
  <script>
    (() => {{
      const overlay = document.getElementById('admin-confirm-overlay');
      const titleEl = document.getElementById('admin-confirm-title');
      const messageEl = document.getElementById('admin-confirm-message');
      const cancelBtn = document.getElementById('admin-confirm-cancel');
      const confirmBtn = document.getElementById('admin-confirm-submit');
      let pendingForm = null;
      let pendingButton = null;

      if (!overlay || !titleEl || !messageEl || !cancelBtn || !confirmBtn) {{
        return;
      }}

      const closeDialog = () => {{
        overlay.classList.add('hidden');
        overlay.classList.remove('flex');
        overlay.setAttribute('aria-hidden', 'true');
        pendingForm = null;
        pendingButton = null;
      }};

      const openDialog = (button, form) => {{
        pendingForm = form;
        pendingButton = button;
        titleEl.textContent = button.dataset.confirmTitle || 'Confirm action';
        messageEl.textContent = button.dataset.confirmMessage || 'Please confirm this action.';
        confirmBtn.innerHTML = button.dataset.confirmCta || '<i class="fa-solid fa-check" aria-hidden="true"></i>Continue';
        overlay.classList.remove('hidden');
        overlay.classList.add('flex');
        overlay.setAttribute('aria-hidden', 'false');
        confirmBtn.focus();
      }};

      document.addEventListener('click', (event) => {{
        const button = event.target.closest('button[data-confirm-title]');
        if (!button) {{
          return;
        }}
        const form = button.closest('form');
        if (!form || button.dataset.confirmed === 'true') {{
          return;
        }}
        event.preventDefault();
        openDialog(button, form);
      }});

      cancelBtn.addEventListener('click', closeDialog);

      confirmBtn.addEventListener('click', () => {{
        if (!pendingForm || !pendingButton) {{
          closeDialog();
          return;
        }}
        pendingButton.dataset.confirmed = 'true';
        pendingButton.disabled = true;
        pendingForm.requestSubmit(pendingButton);
        closeDialog();
      }});

      overlay.addEventListener('click', (event) => {{
        if (event.target === overlay) {{
          closeDialog();
        }}
      }});

      document.addEventListener('keydown', (event) => {{
        if (event.key === 'Escape' && overlay.classList.contains('flex')) {{
          closeDialog();
        }}
      }});
    }})();
  </script>
</body>
</html>"""

    async def _handle_dashboard(self, username: str):
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
              m.email,
              m.slack_username,
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
        email = mentor.get("email") or ""
        slack_username = mentor.get("slack_username") or ""
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
            <form method="POST" action="{self.mentor_action_path}" class="space-y-2 rounded-lg border border-[#E5E5E5] bg-gray-50 p-3">
              <input type="hidden" name="action" value="save">
              <input type="hidden" name="original_github_username" value="{_escape(username)}">
              <label class="block text-[11px] font-semibold uppercase tracking-wide text-gray-500">GitHub</label>
              <input name="github_username" value="{_escape(username)}" class="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs text-gray-800" maxlength="39" required>

              <label class="block text-[11px] font-semibold uppercase tracking-wide text-gray-500">Display name</label>
              <input name="name" value="{_escape(name)}" class="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs text-gray-800" maxlength="100" required>

              <label class="block text-[11px] font-semibold uppercase tracking-wide text-gray-500">Specialties (comma-separated)</label>
              <input name="specialties" value="{_escape(', '.join(str(s) for s in specialties))}" class="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs text-gray-800" maxlength="300">

              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-[11px] font-semibold uppercase tracking-wide text-gray-500">Cap</label>
                  <input name="max_mentees" type="number" min="1" max="10" value="{int(mentor.get('max_mentees') or 3)}" class="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs text-gray-800">
                </div>
                <div class="flex items-end">
                  <label class="inline-flex items-center gap-2 text-xs text-gray-700">
                    <input name="active" type="checkbox" value="1" {'checked' if active else ''}>
                    Published
                  </label>
                </div>
              </div>

              <label class="block text-[11px] font-semibold uppercase tracking-wide text-gray-500">Timezone</label>
              <input name="timezone" value="{_escape(mentor.get('timezone') or '')}" class="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs text-gray-800" maxlength="60">

              <label class="block text-[11px] font-semibold uppercase tracking-wide text-gray-500">Referred by (GitHub)</label>
              <input name="referred_by" value="{_escape(mentor.get('referred_by') or '')}" class="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs text-gray-800" maxlength="39">

              <label class="block text-[11px] font-semibold uppercase tracking-wide text-gray-500">Email</label>
              <input name="email" value="{_escape(email)}" type="email" class="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs text-gray-800" maxlength="255">

              <label class="block text-[11px] font-semibold uppercase tracking-wide text-gray-500">Slack username</label>
              <input name="slack_username" value="{_escape(slack_username)}" class="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs text-gray-800" maxlength="80">

              <div class="flex flex-wrap gap-2 pt-1">
                <button type="submit" class="inline-flex items-center gap-1 rounded-md border border-emerald-200 px-3 py-2 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-50">
                  Save
                </button>
              </div>
            </form>
            <form method="POST" action="{self.mentor_action_path}" class="mt-2">
              <input type="hidden" name="github_username" value="{_escape(username)}">
              <input type="hidden" name="action" value="delete">
              <button
                type="submit"
                data-confirm-title="Delete mentor?"
                data-confirm-message="This permanently removes the mentor record and clears related assignments from the admin panel."
                data-confirm-cta="<i class=&quot;fa-solid fa-trash&quot; aria-hidden=&quot;true&quot;></i>Delete mentor"
                class="inline-flex items-center gap-1 rounded-md border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 transition hover:bg-red-50">
                Delete
              </button>
            </form>
          </td>
        </tr>
        """

    async def _handle_mentor_action(self, request, username: str):
        if not username:
            return self._basic_auth_challenge()

        form = await self._form_data(request)
        github_username = (form.get("github_username") or "").strip().lstrip("@")
        action = (form.get("action") or "").strip().lower()
        if action not in {"save", "delete"}:
            return self._redirect(self.admin_path)

        try:
          if action == "save":
            original_github_username = (form.get("original_github_username") or "").strip().lstrip("@")
            new_github_username = (form.get("github_username") or "").strip().lstrip("@")
            name = (form.get("name") or "").strip()
            specialties_raw = (form.get("specialties") or "").strip()
            timezone = (form.get("timezone") or "").strip()
            referred_by = (form.get("referred_by") or "").strip().lstrip("@")
            email = (form.get("email") or "").strip().lower()
            slack_username = (form.get("slack_username") or "").strip().lstrip("@")
            active = 1 if (form.get("active") or "") == "1" else 0

            if not original_github_username:
              return self._redirect(self.admin_path)
            if not _GH_USERNAME_RE.match(new_github_username):
              return self._redirect(self.admin_path)
            if referred_by and not _GH_USERNAME_RE.match(referred_by):
              return self._redirect(self.admin_path)
            if email and not _EMAIL_RE.match(email):
              return self._redirect(self.admin_path)
            if slack_username and not _SLACK_USERNAME_RE.match(slack_username):
              return self._redirect(self.admin_path)
            specialties_list = [
              item.strip().lower()
              for item in specialties_raw.split(",")
              if item.strip()
            ]
            try:
              max_mentees = int(form.get("max_mentees") or 3)
            except Exception:
              max_mentees = 3
            max_mentees = max(1, min(10, max_mentees))

            await self._d1_run(
              """
              UPDATE mentors
              SET github_username = ?,
                name = ?,
                specialties = ?,
                max_mentees = ?,
                active = ?,
                timezone = ?,
                referred_by = ?,
                email = ?,
                slack_username = ?
              WHERE github_username = ?
              """,
              (
                new_github_username,
                name,
                json.dumps(specialties_list),
                max_mentees,
                active,
                timezone,
                referred_by,
                email,
                slack_username,
                original_github_username,
              ),
            )
            if new_github_username != original_github_username:
              await self._d1_run(
                "UPDATE mentor_assignments SET mentor_login = ? WHERE mentor_login = ?",
                (new_github_username, original_github_username),
              )
          else:
                await self._d1_run("DELETE FROM mentor_assignments WHERE mentor_login = ?", (github_username,))
                await self._d1_run("DELETE FROM mentors WHERE github_username = ?", (github_username,))
        except Exception as exc:
            console.error(f"[AdminService] Mentor action '{action}' failed for {github_username}: {exc}")

        return self._redirect(self.admin_path)
