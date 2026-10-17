import json
import unittest


class SendGridEmailServiceTests(unittest.TestCase):
    def test_sendgrid_payload_uses_web_api_shape_without_exposing_api_key(self):
        from src.email_service import build_sendgrid_payload

        payload = build_sendgrid_payload(
            to_email="reader@example.com",
            subject="BLT Digest",
            html_content="<p>Hello</p>",
            from_email="newsletter@example.com",
            from_name="BLT Newsletter",
            custom_args={"job_id": "job_123"},
        )

        self.assertEqual(payload["personalizations"][0]["to"][0]["email"], "reader@example.com")
        self.assertEqual(payload["from"], {"email": "newsletter@example.com", "name": "BLT Newsletter"})
        self.assertEqual(payload["subject"], "BLT Digest")
        self.assertEqual(payload["content"], [{"type": "text/html", "value": "<p>Hello</p>"}])
        self.assertEqual(payload["custom_args"], {"job_id": "job_123"})
        self.assertNotIn("api_key", json.dumps(payload).lower())
        self.assertNotIn("bearer", json.dumps(payload).lower())

    def test_newsletter_template_escapes_dynamic_text_and_adds_unsubscribe_footer(self):
        from src.email_templates import render_newsletter_campaign_email

        html = render_newsletter_campaign_email(
            title="<script>alert(1)</script>",
            summary="BLT updates & contributor news",
            markdown_body="# Hello\n\nA shipped update.",
            archive_url="https://newsletter.example/archive/hello",
            unsubscribe_url="https://newsletter.example/unsubscribe/token",
        )

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("BLT updates &amp; contributor news", html)
        self.assertIn("<h1>Hello</h1>", html)
        self.assertIn("A shipped update.", html)
        self.assertIn("unsubscribe", html.lower())
        self.assertIn("https://newsletter.example/archive/hello", html)

    def test_campaign_records_are_d1_safe_and_queue_messages_do_not_include_raw_email(self):
        from src.email_campaigns import build_delivery_event_record, build_queue_message, build_send_job_record

        job = build_send_job_record("cmp_123", 2, "adm_1")
        event = build_delivery_event_record(job["id"], "sub_1", "queued")
        message = build_queue_message(job["id"], "cmp_123", event["id"], "sub_1")

        for record in [job, event, message]:
            self.assertNotIn(None, record.values())

        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["provider"], "sendgrid")
        self.assertEqual(job["total_recipients"], 2)
        self.assertEqual(event["event_type"], "queued")
        self.assertEqual(job["campaign_id"], "cmp_123")
        self.assertEqual(message["campaign_id"], "cmp_123")
        self.assertNotIn("email", message)
        self.assertEqual(message["subscriber_id"], "sub_1")


if __name__ == "__main__":
    unittest.main()
