"""Regression tests for the notifications dropdown in includes/header.html.

Notification messages can carry user-supplied text (usernames, team names,
kudos comments), so the dropdown must render them as text, never as HTML, and
must only follow same-origin or http(s) links.
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

from website.models import Notification

HEADER = Path(settings.BASE_DIR) / "website" / "templates" / "includes" / "header.html"
PAYLOAD = '<img src=x onerror="alert(1)">'


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


class NotificationDropdownTemplateTest(TestCase):
    def setUp(self):
        self.source = HEADER.read_text()

    def test_message_not_interpolated_into_html(self):
        self.assertNotRegex(self.source, r"\$\{\s*notification\.message\s*\}")
        self.assertNotRegex(self.source, r"\$\{\s*notification\.id\s*\}")
        self.assertIn("messageEl.textContent", self.source)

    def test_link_goes_through_safe_check(self):
        self.assertNotIn("window.location.href = notification.link", self.source)
        self.assertIn("safeNotificationLink(notification.link)", self.source)

    @skipUnless(shutil.which("node"), "node not installed")
    def test_safe_notification_link_rejects_script_urls(self):
        fn = _extract_function(self.source, "safeNotificationLink")
        cases = {
            "/profile/alice": "/profile/alice",
            "https://owaspblt.org/x": "https://owaspblt.org/x",
            "javascript:alert(1)": None,
            " JavaScript:alert(1)": None,
            "data:text/html,<script>alert(1)</script>": None,
            "//evil.example/": None,
            "/\\evil.example/": None,
            "": None,
        }
        script = fn + f"\nconsole.log(JSON.stringify({json.dumps(list(cases))}.map(safeNotificationLink)));"
        out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out), list(cases.values()))


class FetchNotificationsTest(TestCase):
    def test_message_returned_as_data_and_page_renders(self):
        user = User.objects.create_user(username="notif-user", password="pw")
        Notification.objects.create(user=user, message=PAYLOAD, link="javascript:alert(1)")
        self.client.force_login(user)

        data = self.client.get(reverse("fetch_notifications")).json()
        self.assertEqual(data["notifications"][0]["message"], PAYLOAD)

        page = self.client.get(reverse("terms")).content.decode()
        self.assertIn("safeNotificationLink", page)
        self.assertIsNone(re.search(r"\$\{\s*notification\.message\s*\}", page))


class OtherTemplateSinksTest(TestCase):
    """Same class of bug found by the follow-up grep: user/GitHub text interpolated into innerHTML."""

    TEMPLATES = Path(settings.BASE_DIR) / "website" / "templates"

    def test_messaging_renders_messages_as_text(self):
        source = (self.TEMPLATES / "messaging.html").read_text()
        self.assertNotRegex(source, r"innerHTML\s*=\s*`[^`]*\$\{\s*(data|message)\.username")
        self.assertNotRegex(source, r"innerHTML\s*=\s*`[^`]*\$\{\s*(data\.content|decryptedContent)")
        self.assertIn("renderMessageContent(", source)

    def test_bounties_list_escapes_github_issue_fields(self):
        source = (self.TEMPLATES / "bounties_list.html").read_text()
        for raw in ("${issue.title}", "Opened by ${issue.user}", "${issue.url}", "${label}"):
            self.assertNotIn(raw, source)
