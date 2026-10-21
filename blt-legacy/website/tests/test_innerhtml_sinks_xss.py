"""Regression tests for innerHTML / template-string sinks left open after the
notification-dropdown fix (see test_notification_dropdown_xss.py).

Each page below used to interpolate user- or API-controlled text (usernames,
team/organization names, check-in text, GitHub contributor data, reaction keys,
URL query parameters) into innerHTML, jQuery .html()/.append(), or a JS template
literal. These tests pin the fixes at the source level, exercise the URL/escape
helpers under node, and render the riskiest pages with hostile data.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from website.models import Organization

TEMPLATES = Path(settings.BASE_DIR) / "website" / "templates"
STATIC_JS = Path(settings.BASE_DIR) / "website" / "static" / "js"
PAYLOAD = '<img src=x onerror="alert(1)">'
SCRIPT_BREAKOUT = "</script><script>alert(1)</script>"

URL_CASES = {
    "https://github.com/OWASP-BLT/BLT/issues/1": "https://github.com/OWASP-BLT/BLT/issues/1",
    "http://avatars.example/u/1": "http://avatars.example/u/1",
    "javascript:alert(1)": None,
    " JavaScript:alert(1)": None,
    "data:text/html,<script>alert(1)</script>": None,
    "vbscript:msgbox(1)": None,
    "": None,
}


def _read(path):
    return Path(path).read_text()


def _extract_function(source, name):
    start = source.index(f"function {name}(")
    depth = 0
    for i in range(source.index("{", start), len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise AssertionError(f"could not extract {name}")


def _run_node(script):
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True, timeout=30).stdout
    return json.loads(out)


class TemplateSourceTest(TestCase):
    """The raw interpolations that made each sink exploitable are gone."""

    def test_team_overview_search_results_rendered_as_text(self):
        source = _read(TEMPLATES / "team_overview.html")
        self.assertNotIn("${user.username}", source)
        self.assertNotIn('dark:text-gray-300">${username}</span>', source)
        self.assertNotIn("selectUser('${", source)
        self.assertIn("function renderUserResults(", source)
        self.assertIn("item.textContent", source)
        self.assertIn("encodeURIComponent(query)", source)

    def test_bid_selection_builds_cards_with_dom(self):
        source = _read(TEMPLATES / "bid_selection.html")
        self.assertNotRegex(source, r"innerHTML\s*=\s*`[^`]*\$\{bid\.")
        self.assertIn("safeHttpUrl(issueUrl)", source)

    def test_sizzle_checkin_escapes_fields(self):
        source = _read(TEMPLATES / "sizzle" / "checkin.html")
        for field in ("username", "previous_work", "next_plan", "blockers"):
            self.assertNotIn("${item.%s}" % field, source)
            self.assertIn("${escapeHtml(item.%s)}" % field, source)

    def test_sizzle_report_escapes_fields(self):
        source = _read(TEMPLATES / "sizzle" / "sizzle.html")
        self.assertNotIn("${item.issue_title}", source)
        self.assertIn("${escapeHtml(item.issue_title)}", source)

    def test_time_logs_org_names_not_inlined(self):
        source = _read(TEMPLATES / "sizzle" / "time_logs.html")
        self.assertNotIn("organizations_list | safe", source)
        self.assertNotIn("organizations_list|safe", source)
        self.assertIn('json_script:"organizations-list-data"', source)
        self.assertNotIn(".html(`Selected organization: ${result.name}", source)
        self.assertNotRegex(source, r"<p class=\"text-sm\">\$\{message\}</p>")

    def test_slack_integration_message_as_text(self):
        source = _read(TEMPLATES / "organization" / "dashboard" / "add_slack_integration.html")
        self.assertNotIn("${data.message}", source)
        self.assertIn("document.createTextNode(data.message", source)
        self.assertIn("safeHttpUrl(user.avatar)", source)

    def test_repo_detail_contributors_built_with_dom(self):
        source = _read(STATIC_JS / "repo_detail.js")
        for raw in (
            "${contributor.name}",
            "${contributor.avatar_url}",
            "${contributor.github_url}",
            "${stat.contributor.name}",
            "${stat.contributor.avatar_url}",
            "${stat.contributor.github_id}",
        ):
            self.assertNotIn(raw, source)
        self.assertIn("safeHttpUrl(contributor.avatar_url)", source)
        self.assertIn("safeHttpUrl(contributor.github_url)", source)

    def test_incident_print_does_not_write_title_as_html(self):
        source = _read(TEMPLATES / "security" / "incidents" / "incident_detail.html")
        self.assertNotIn("<title>{{ incident.title|escapejs }}</title>", source)
        self.assertNotIn("${content}", source)
        self.assertIn('printDoc.title = "{{ incident.title|escapejs }}"', source)

    def test_organization_detail_error_as_text(self):
        source = _read(TEMPLATES / "organization" / "organization_detail.html")
        self.assertNotIn("Error: ${err.message}</div>", source)
        self.assertIn("appendStatusError(statusMessages", source)
        self.assertIn("updateGithubRepos('{{ organization.slug|escapejs }}')", source)

    def test_report_hash_param_not_interpolated(self):
        source = _read(TEMPLATES / "report.html")
        self.assertNotIn('value="${hashValue}"', source)
        self.assertNotIn("uploads/${hashValue}", source)
        self.assertIn("/^[A-Za-z0-9_-]+$/.test(hashValue)", source)
        self.assertNotIn("previewFile('${safeName}')", source)
        self.assertNotIn("<span>${message}</span>", source)

    def test_join_room_reaction_keys_as_text(self):
        source = _read(TEMPLATES / "join_room.html")
        self.assertNotIn('<span class="mr-1">${emoji}</span>', source)
        self.assertNotIn("innerHTML = `<span>${emoji}</span>`", source)
        self.assertNotIn("button.innerHTML = emoji", source)

    def test_hunt_submission_escapes_duplicate_bug_fields(self):
        source = _read(TEMPLATES / "hunt_submittion.html")
        self.assertIn("sanitizeInput(trint\n              .description)", source)
        self.assertNotRegex(source, r"Description: \" \+ trint\s*\.description")

    def test_ossh_results_json_not_parsed_as_html(self):
        source = _read(TEMPLATES / "ossh" / "results.html")
        self.assertNotRegex(source, r"Container\.innerHTML\s*=\s*html")
        self.assertNotIn('github_username: "{{ username }}"', source)

    def test_domain_user_options_escaped(self):
        for name in ("add_domain.html", "edit_domain.html"):
            source = _read(TEMPLATES / "organization" / "dashboard" / name)
            self.assertNotIn('`<option value="{{ user.email }}">{{ user.username }}', source)
            self.assertIn('username: "{{ user.username|escapejs }}"', source)

    def test_misc_sinks(self):
        self.assertNotIn(
            "${data.project_name}",
            _read(TEMPLATES / "slack_channels.html"),
        )
        self.assertNotIn(
            "${data.output || 'No output returned'}",
            _read(TEMPLATES / "management_commands.html"),
        )
        self.assertNotIn("${comment_author}", _read(TEMPLATES / "comments2.html"))
        self.assertNotIn("${message}</span>", _read(TEMPLATES / "projects" / "project_list.html"))
        self.assertNotIn("${error.message", _read(STATIC_JS / "organization_team_overview.js"))
        self.assertNotIn(
            "marked(`{{ hunt_obj.description }}`", _read(TEMPLATES / "organization" / "bughunt" / "view_bughunt.html")
        )

    def test_header_recent_searches_has_escape_helper_in_scope(self):
        source = _read(TEMPLATES / "includes" / "header.html")
        start = source.index("// Recent Searches Dropdown Functionality")
        end = source.index("</script>", start)
        self.assertIn("function escapeHtml(", source[start:end])


@skipUnless(shutil.which("node"), "node not installed")
class HelperBehaviourTest(TestCase):
    def _check_url_helper(self, fn, name, prelude=""):
        script = prelude + fn + f"\nconsole.log(JSON.stringify({json.dumps(list(URL_CASES))}.map({name})));"
        self.assertEqual(_run_node(script), list(URL_CASES.values()))

    def test_bid_selection_safe_http_url(self):
        fn = _extract_function(_read(TEMPLATES / "bid_selection.html"), "safeHttpUrl")
        self._check_url_helper(fn, "safeHttpUrl")

    def test_slack_integration_safe_http_url(self):
        fn = _extract_function(
            _read(TEMPLATES / "organization" / "dashboard" / "add_slack_integration.html"), "safeHttpUrl"
        )
        self._check_url_helper(fn, "safeHttpUrl")

    def test_repo_detail_safe_http_url(self):
        fn = _extract_function(_read(STATIC_JS / "repo_detail.js"), "safeHttpUrl")
        prelude = 'const window = { location: { href: "https://owaspblt.org/repository/blt/" } };\n'
        self._check_url_helper(fn, "safeHttpUrl", prelude)
        # Relative URLs resolve against the page (same origin), never to another scheme.
        script = prelude + fn + '\nconsole.log(JSON.stringify(["/static/a.png", "//evil.example/x"].map(safeHttpUrl)));'
        self.assertEqual(
            _run_node(script),
            ["https://owaspblt.org/static/a.png", "https://evil.example/x"],
        )

    def test_team_overview_js_safe_image_url(self):
        fn = _extract_function(_read(STATIC_JS / "organization_team_overview.js"), "safeImageUrl")
        cases = {
            "/media/avatars/a.png": "/media/avatars/a.png",
            "https://avatars.githubusercontent.com/u/1": "https://avatars.githubusercontent.com/u/1",
            'x" onerror="alert(1)': None,
            "javascript:alert(1)": None,
            "//evil.example/a.png": None,
            "/\\evil.example/a.png": None,
        }
        script = fn + f"\nconsole.log(JSON.stringify({json.dumps(list(cases))}.map(safeImageUrl)));"
        self.assertEqual(_run_node(script), list(cases.values()))

    def test_escape_helpers_neutralise_markup(self):
        sources = {
            "checkin": _read(TEMPLATES / "sizzle" / "checkin.html"),
            "sizzle": _read(TEMPLATES / "sizzle" / "sizzle.html"),
            "add_domain": _read(TEMPLATES / "organization" / "dashboard" / "add_domain.html"),
        }
        values = [PAYLOAD, "a\"b'c", None, 42]
        for label, source in sources.items():
            with self.subTest(template=label):
                fn = _extract_function(source, "escapeHtml")
                out = _run_node(fn + f"\nconsole.log(JSON.stringify({json.dumps(values)}.map(escapeHtml)));")
                self.assertEqual(
                    out,
                    [
                        "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
                        "a&quot;b&#39;c",
                        "",
                        "42",
                    ],
                )


class RenderedPagesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sink-user", password="pw")
        self.client.force_login(self.user)

    def test_time_logs_keeps_hostile_org_name_inside_json(self):
        Organization.objects.create(name=SCRIPT_BREAKOUT, url="https://evil.example/")
        response = self.client.get(reverse("time_logs"))
        self.assertEqual(response.status_code, 200)
        page = response.content.decode()
        self.assertNotIn(SCRIPT_BREAKOUT, page)
        self.assertIn('id="organizations-list-data"', page)
        match = re.search(r'<script id="organizations-list-data" type="application/json">(.*?)</script>', page, re.S)
        self.assertIsNotNone(match)
        names = [org["name"] for org in json.loads(match.group(1))]
        self.assertIn(SCRIPT_BREAKOUT, names)

    def test_search_users_returns_team_name_as_data(self):
        team = Organization.objects.create(name=PAYLOAD, url="https://team.example/", type="team")
        self.user.userprofile.team = team
        self.user.userprofile.save()
        data = self.client.get(reverse("search_users"), {"query": "sink"}).json()
        self.assertEqual(data, [{"username": "sink-user", "team": PAYLOAD}])

    def test_team_overview_page_uses_text_renderer(self):
        page = self.client.get(reverse("team_overview")).content.decode()
        self.assertIn("renderUserResults", page)
        self.assertNotIn("${user.username}", page)
