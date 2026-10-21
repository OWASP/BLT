"""Daily check-in reminders: due-time rules, the scheduler run against a real SQLite copy
of the D1 schema (all migrations applied), email rendering and provider requests."""
import asyncio
import base64
import json
import logging
import sqlite3
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKERS = ROOT / "workers"
if str(WORKERS) not in sys.path:
    sys.path.insert(0, str(WORKERS))

import email_service  # noqa: E402
import reminders  # noqa: E402
import scheduler  # noqa: E402
from email_service import EmailService, build_provider_request, parse_from_address  # noqa: E402
from reminders import normalize_days, parse_days, reminder_due, render_reminder_email, to_local  # noqa: E402

MON_SAT = "1,2,3,4,5,6"


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def enc(value):
    """Same storage format as main.encrypt_data."""
    return "aXY=:" + base64.b64encode(value.encode()).decode()


class TestToLocal(unittest.TestCase):
    def test_offsets_including_dst_and_quarter_hour_zones(self):
        cases = [
            (utc(2026, 10, 20, 15, 30), "America/New_York", "2026-10-20 11:30"),   # EDT, UTC-4
            (utc(2026, 12, 1, 16, 30), "America/New_York", "2026-12-01 11:30"),    # EST, UTC-5
            (utc(2026, 10, 20, 6, 0), "Asia/Kolkata", "2026-10-20 11:30"),         # UTC+5:30
            (utc(2026, 10, 20, 5, 45), "Asia/Kathmandu", "2026-10-20 11:30"),      # UTC+5:45
            (utc(2026, 10, 20, 22, 30), "Pacific/Auckland", "2026-10-21 11:30"),   # NZDT, next day
            (utc(2026, 10, 20, 11, 30), "UTC", "2026-10-20 11:30"),
        ]
        for now, tz, expected in cases:
            self.assertEqual(to_local(now, tz).strftime("%Y-%m-%d %H:%M"), expected, tz)


class TestReminderDue(unittest.TestCase):
    def due(self, now, tz="America/New_York", time="11:30", days=MON_SAT, last=None):
        return reminder_due(now, tz, time, days, last)

    def test_due_at_local_time_not_utc_time(self):
        # 2026-10-20 is a Tuesday. 11:30 New York (EDT) is 15:30 UTC.
        self.assertEqual(self.due(utc(2026, 10, 20, 15, 15))[0], False)
        self.assertEqual(self.due(utc(2026, 10, 20, 15, 30)), (True, "2026-10-20", "due"))
        # 11:30 UTC is 07:30 in New York: not yet.
        self.assertEqual(self.due(utc(2026, 10, 20, 11, 30))[2], "not_yet")

    def test_same_local_time_moves_in_utc_across_dst(self):
        # After the November fall-back, 11:30 EST is 16:30 UTC.
        self.assertFalse(self.due(utc(2026, 11, 3, 15, 30))[0])
        self.assertTrue(self.due(utc(2026, 11, 3, 16, 30))[0])
        # Before the March spring-forward (EST) and after it (EDT).
        self.assertTrue(self.due(utc(2026, 3, 6, 16, 30))[0])
        self.assertTrue(self.due(utc(2026, 3, 10, 15, 30))[0])
        self.assertFalse(self.due(utc(2026, 3, 10, 14, 30))[0])

    def test_reminder_inside_the_spring_forward_gap_goes_out_after_it(self):
        # 2026-03-08 New York: 02:00 jumps to 03:00, so 02:30 never happens.
        # 06:45 UTC = 01:45 EST: not yet. 07:00 UTC = 03:00 EDT: send.
        days = "1,2,3,4,5,6,7"
        self.assertFalse(self.due(utc(2026, 3, 8, 6, 45), time="02:30", days=days)[0])
        self.assertEqual(self.due(utc(2026, 3, 8, 7, 0), time="02:30", days=days), (True, "2026-03-08", "due"))

    def test_repeated_fall_back_hour_does_not_send_twice(self):
        # 2026-11-01 New York: 01:30 happens at 05:30 UTC (EDT) and again at 06:30 UTC (EST).
        days = "1,2,3,4,5,6,7"
        first = self.due(utc(2026, 11, 1, 5, 30), time="01:30", days=days)
        self.assertEqual(first, (True, "2026-11-01", "due"))
        second = self.due(utc(2026, 11, 1, 6, 30), time="01:30", days=days, last=first[1])
        self.assertEqual(second, (False, "2026-11-01", "already_sent"))

    def test_sunday_is_skipped_for_monday_to_saturday(self):
        # 2026-10-25 is a Sunday, 2026-10-24 a Saturday, 2026-10-26 a Monday.
        self.assertEqual(self.due(utc(2026, 10, 25, 15, 30))[2], "day_off")
        self.assertTrue(self.due(utc(2026, 10, 24, 15, 30))[0])
        self.assertTrue(self.due(utc(2026, 10, 26, 15, 30))[0])
        # The weekday is the user's local one: 01:00 UTC Monday is still Sunday in New York.
        self.assertEqual(self.due(utc(2026, 10, 26, 1, 0), time="20:30")[2], "day_off")

    def test_once_per_local_day_and_window(self):
        self.assertEqual(self.due(utc(2026, 10, 20, 15, 45), last="2026-10-20")[2], "already_sent")
        self.assertTrue(self.due(utc(2026, 10, 20, 15, 45), last="2026-10-19")[0])
        # A run that comes more than two hours late doesn't send a stale reminder.
        self.assertEqual(self.due(utc(2026, 10, 20, 17, 45))[2], "window_passed")

    def test_days_parsing_and_validation(self):
        self.assertEqual(parse_days(None), (1, 2, 3, 4, 5, 6, 7))
        self.assertEqual(parse_days("6,1,3"), (1, 3, 6))
        self.assertEqual(normalize_days([6, "1", 2, 3, 4, 5]), MON_SAT)
        self.assertEqual(normalize_days("1,2,3,4,5,6"), MON_SAT)
        for bad in [[], [0], [8], ["x"], [True], "", {"1": 1}]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                normalize_days(bad)


class TestReminderEmail(unittest.TestCase):
    def test_subject_link_text_part_and_settings_link(self):
        subject, html_body, text_body = render_reminder_email(
            "https://sizzle.owaspblt.org", display_name="Donnie <b>", local_date="2026-10-20",
            notification_time="11:30", days=MON_SAT, tz_name="America/New_York",
        )
        self.assertEqual(subject, "Daily check-in reminder for 2026-10-20")
        for body in (html_body, text_body):
            self.assertIn("https://sizzle.owaspblt.org/app", body)
            self.assertIn("https://sizzle.owaspblt.org/settings", body)
            self.assertIn("11:30 (America/New_York), Monday to Saturday", body)
        self.assertIn("stop these emails", text_body)
        self.assertNotIn("<b>", html_body)
        self.assertIn("Donnie &lt;b&gt;", html_body)
        self.assertNotIn("<", text_body.replace("Donnie <b>", ""))


class TestProviders(unittest.TestCase):
    ARGS = dict(api_key="KEY-123", from_email="noreply@owaspblt.org", from_name="BLT Sizzle",
                to_email="dev@example.com", subject="S", html_content="<p>h</p>", text_content="t",
                custom_args={"purpose": "daily_reminder"})

    def test_each_provider_builds_a_request_with_text_and_html(self):
        url, headers, body = build_provider_request("sendgrid", **self.ARGS)
        self.assertEqual(url, "https://api.sendgrid.com/v3/mail/send")
        self.assertEqual(headers["Authorization"], "Bearer KEY-123")
        content = json.loads(body)["content"]
        self.assertEqual([c["type"] for c in content], ["text/plain", "text/html"])

        url, headers, body = build_provider_request("resend", **self.ARGS)
        payload = json.loads(body)
        self.assertEqual(url, "https://api.resend.com/emails")
        self.assertEqual(payload["from"], "BLT Sizzle <noreply@owaspblt.org>")
        self.assertEqual((payload["text"], payload["html"], payload["to"]), ("t", "<p>h</p>", ["dev@example.com"]))

        url, headers, body = build_provider_request("mailtrap", **self.ARGS)
        payload = json.loads(body)
        self.assertEqual(url, "https://send.api.mailtrap.io/api/send")
        self.assertEqual(payload["from"], {"email": "noreply@owaspblt.org", "name": "BLT Sizzle"})
        self.assertEqual(payload["category"], "daily_reminder")

        url, headers, body = build_provider_request("mailgun", **self.ARGS)
        self.assertEqual(url, "https://api.mailgun.net/v3/owaspblt.org/messages")
        self.assertTrue(headers["Authorization"].startswith("Basic "))
        self.assertIn("text=t", body)
        url, _, _ = build_provider_request("mailgun", domain="mg.owaspblt.org",
                                           api_base="https://api.eu.mailgun.net", **self.ARGS)
        self.assertEqual(url, "https://api.eu.mailgun.net/v3/mg.owaspblt.org/messages")

    def test_from_address_forms(self):
        self.assertEqual(parse_from_address("BLT <noreply@owaspblt.org>"), ("noreply@owaspblt.org", "BLT"))
        self.assertEqual(parse_from_address("noreply@owaspblt.org", "Sizzle"), ("noreply@owaspblt.org", "Sizzle"))

    def _service(self, statuses, provider="sendgrid"):
        calls = []

        async def transport(url, headers, body):
            calls.append((url, headers, body))
            return statuses[min(len(calls) - 1, len(statuses) - 1)]

        return EmailService(provider, "KEY-123", "BLT <noreply@owaspblt.org>", transport=transport), calls

    def send(self, service):
        return asyncio.run(service.send_email("dev@example.com", "S", "<p>h</p>", text_content="t"))

    def test_transient_failure_is_retried_once(self):
        service, calls = self._service([(500, "oops"), (202, "")])
        result = self.send(service)
        self.assertTrue(result["success"])
        self.assertEqual((len(calls), result["attempts"]), (2, 2))

        service, calls = self._service([(503, "down")])
        result = self.send(service)
        self.assertFalse(result["success"])
        self.assertEqual(len(calls), 2, "at most one retry")

    def test_permanent_failure_is_not_retried_and_hides_key_and_recipient(self):
        body = '{"errors":[{"message":"The from address does not match a verified Sender Identity. dev@example.com"}]}'
        service, calls = self._service([(403, body)])
        result = self.send(service)
        self.assertEqual(len(calls), 1)
        self.assertFalse(result["success"])
        self.assertTrue(result["permanent_failure"])
        self.assertIn("verified Sender Identity", result["detail"])
        self.assertNotIn("dev@example.com", result["detail"])
        self.assertNotIn("KEY-123", json.dumps(result))

    def test_unsupported_or_unconfigured_provider_sends_nothing(self):
        service, calls = self._service([(202, "")], provider="pigeon")
        self.assertEqual(self.send(service)["error"], "Email provider is not supported.")
        service = EmailService("sendgrid", "", "noreply@owaspblt.org")
        self.assertEqual(asyncio.run(service.send_email("a@b.org", "S", "h"))["status"], 503)
        self.assertEqual(calls, [])

    def test_from_env_reads_email_secrets(self):
        env = types.SimpleNamespace(EMAIL_PROVIDER=" Resend ", EMAIL_API_KEY="k", EMAIL_FROM="x@owaspblt.org")
        service = EmailService.from_env(env)
        self.assertEqual(service.provider, "resend")
        self.assertTrue(service.is_configured())
        self.assertEqual(service.describe(), {"provider": "resend", "supported": True,
                                              "api_key_present": True, "from_domain": "owaspblt.org"})


# ---------------------------------------------------------------- scheduler against SQLite


class _Stmt:
    def __init__(self, conn, sql, params=()):
        self.conn, self.sql, self.params = conn, sql, params

    def bind(self, *params):
        return _Stmt(self.conn, self.sql, params)

    async def all(self):
        await asyncio.sleep(0)  # let overlapping runs interleave like real I/O
        cur = self.conn.execute(self.sql, self.params)
        cols = [c[0] for c in cur.description]
        return {"results": [dict(zip(cols, row)) for row in cur.fetchall()]}

    async def first(self):
        rows = (await self.all())["results"]
        return rows[0] if rows else None

    async def run(self):
        await asyncio.sleep(0)
        cur = self.conn.execute(self.sql, self.params)
        self.conn.commit()
        return {"meta": {"changes": cur.rowcount}}


class FakeD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        for migration in sorted((ROOT / "migrations").glob("*.sql")):
            self.conn.executescript(migration.read_text())

    def prepare(self, sql):
        return _Stmt(self.conn, sql)


class FakeEmail:
    def __init__(self, results=None):
        self.sent = []
        self.results = list(results or [])

    async def send_email(self, to_email, subject, html_content, custom_args=None, text_content=None):
        self.sent.append({"to": to_email, "subject": subject, "html": html_content, "text": text_content})
        result = self.results.pop(0) if self.results else {"success": True, "status": 202}
        return dict(result, provider="fake")


class TestSchedulerRun(unittest.TestCase):
    def setUp(self):
        self.db = FakeD1()
        self.env = types.SimpleNamespace(sizzle_db=self.db, WORKER_HOST="sizzle.owaspblt.org")
        self.db.conn.execute(
            "INSERT INTO users (user_id, github_id, encrypted_email, notification_time, notification_days,"
            " timezone, email_notifications) VALUES (?, ?, ?, '11:30', ?, 'America/New_York', 1)",
            ("DonnieBLT", "1", enc("donnie@example.org"), MON_SAT),
        )
        self.db.conn.commit()

    def run_at(self, now, email=None, slack_post=None):
        email = email or FakeEmail()
        summary = asyncio.run(scheduler.run_user_reminders(self.env, now, email_service=email, slack_post=slack_post))
        return summary, email

    def user(self):
        cur = self.db.conn.execute("SELECT last_reminder_date, last_reminder_status FROM users WHERE user_id='DonnieBLT'")
        return cur.fetchone()

    def test_migration_defaults_existing_users_to_every_day(self):
        self.db.conn.execute("INSERT INTO users (user_id) VALUES ('legacy')")
        row = self.db.conn.execute("SELECT notification_days FROM users WHERE user_id='legacy'").fetchone()
        self.assertEqual(row[0], "1,2,3,4,5,6,7")

    def test_sends_once_at_local_time_and_never_twice_the_same_day(self):
        _, email = self.run_at(utc(2026, 10, 20, 15, 15))
        self.assertEqual(email.sent, [])
        summary, email = self.run_at(utc(2026, 10, 20, 15, 30))
        self.assertEqual(summary["sent"], 1)
        self.assertEqual(len(email.sent), 1)
        self.assertEqual(email.sent[0]["to"], "donnie@example.org")
        self.assertIn("https://sizzle.owaspblt.org/app", email.sent[0]["text"])
        self.assertEqual(self.user(), ("2026-10-20", "sent"))
        for minute in (45,):
            _, again = self.run_at(utc(2026, 10, 20, 15, minute))
            self.assertEqual(again.sent, [])
        _, again = self.run_at(utc(2026, 10, 20, 16, 0))
        self.assertEqual(again.sent, [])
        # Next day it goes out again.
        _, next_day = self.run_at(utc(2026, 10, 21, 15, 30))
        self.assertEqual(len(next_day.sent), 1)

    def test_sunday_is_skipped(self):
        for hour, minute in [(15, 30), (15, 45), (16, 0), (17, 0)]:
            _, email = self.run_at(utc(2026, 10, 25, hour, minute))
            self.assertEqual(email.sent, [])
        self.assertEqual(self.user(), (None, None))

    def test_already_checked_in_today_is_not_reminded(self):
        self.db.conn.execute("INSERT INTO checkins (user_id, checkin_date) VALUES ('DonnieBLT', '2026-10-20')")
        summary, email = self.run_at(utc(2026, 10, 20, 15, 30))
        self.assertEqual((email.sent, summary["skipped_checked_in"]), ([], 1))

    def test_failed_send_is_recorded_and_not_resent_by_later_runs(self):
        failing = FakeEmail([{"success": False, "status": 403, "error": "sendgrid returned status 403.",
                              "attempts": 1, "detail": "sender not verified"}])
        with self.assertLogs(scheduler.logger, level=logging.ERROR) as logs:
            summary, _ = self.run_at(utc(2026, 10, 20, 15, 30), email=failing)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(self.user(), ("2026-10-20", "failed"))
        self.assertIn("status=403", "\n".join(logs.output))
        _, again = self.run_at(utc(2026, 10, 20, 15, 45))
        self.assertEqual(again.sent, [])

    def test_missing_email_address_is_logged_as_failed(self):
        self.db.conn.execute("UPDATE users SET encrypted_email = '' WHERE user_id='DonnieBLT'")
        summary, email = self.run_at(utc(2026, 10, 20, 15, 30))
        self.assertEqual(email.sent, [])
        self.assertEqual(self.user(), ("2026-10-20", "failed"))

    def test_slack_only_user_and_disallowed_webhook(self):
        posts = []

        async def post(url, headers, body):
            posts.append(url)
            return 200, "ok"

        self.db.conn.execute(
            "INSERT INTO users (user_id, encrypted_slack_webhook_url, notification_time, timezone, email_notifications)"
            " VALUES ('slacker', ?, '09:00', 'UTC', 0), ('evil', ?, '09:00', 'UTC', 0)",
            (enc("https://hooks.slack.com/services/T/B/x"), enc("https://evil.example/services/x")),
        )
        self.db.conn.commit()
        self.run_at(utc(2026, 10, 20, 9, 0), slack_post=post)
        self.assertEqual(posts, ["https://hooks.slack.com/services/T/B/x"])

    def test_two_overlapping_runs_claim_the_day_once(self):
        async def both():
            first, second = FakeEmail(), FakeEmail()
            await asyncio.gather(
                scheduler.run_user_reminders(self.env, utc(2026, 10, 20, 15, 30), email_service=first),
                scheduler.run_user_reminders(self.env, utc(2026, 10, 20, 15, 30), email_service=second),
            )
            return len(first.sent) + len(second.sent)

        self.assertEqual(asyncio.run(both()), 1)

    def test_unverified_signup_email_is_not_used(self):
        user = {"email": "new@example.org", "email_verified": 0, "encrypted_email": ""}
        self.assertEqual(scheduler.reminder_email_address(user), "")
        user["email_verified"] = 1
        self.assertEqual(scheduler.reminder_email_address(user), "new@example.org")


class TestOrgNotifications(unittest.TestCase):
    def test_org_reminder_runs_in_one_quarter_hour_slot(self):
        db = FakeD1()
        db.conn.execute("INSERT INTO organizations (github_org_name, name, slug, encrypted_slack_webhook_url)"
                        " VALUES ('owasp-blt', 'OWASP BLT', 'owasp-blt', ?)",
                        (enc("https://hooks.slack.com/services/T/B/org"),))
        db.conn.execute("INSERT INTO users (user_id) VALUES ('a')")
        db.conn.execute("INSERT INTO user_organizations (user_id, org_id, status) VALUES ('a', 1, 'approved')")
        db.conn.commit()
        env = types.SimpleNamespace(sizzle_db=db)
        posts = []

        async def post(url, headers, body):
            posts.append(json.loads(body))
            return 200, "ok"

        for minute in (0, 15, 30, 45):
            asyncio.run(scheduler.handle_org_notifications(env, utc(2026, 10, 20, 9, minute), post=post))
        self.assertEqual(len(posts), 1)
        self.assertIn("@a", posts[0]["blocks"][0]["text"]["text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
