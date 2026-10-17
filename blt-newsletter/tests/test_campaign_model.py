import unittest
from pathlib import Path

from src.newsletter_campaign_schema import (
    campaign_insert_columns_and_params,
    campaign_order_expression,
    campaign_select_columns,
    campaign_slug_column,
    map_campaign_update_fields,
    send_job_campaign_column,
)


ROOT = Path(__file__).resolve().parents[1]

CAMPAIGN_COLUMNS = [
    "id",
    "slug",
    "title",
    "subject",
    "summary",
    "status",
    "markdown_body",
    "html_body",
    "scheduled_for",
    "published_at",
    "sent_at",
    "created_by_admin_id",
    "created_at",
    "updated_at",
    "metadata_json",
]

LEGACY_COLUMNS = [
    "id",
    "issue_slug",
    "title",
    "subject",
    "status",
    "markdown_body",
    "html_body",
    "scheduled_for",
    "sent_at",
    "created_by_admin_id",
    "created_at",
    "updated_at",
    "metadata_json",
]

CAMPAIGN_RECORD = {
    "id": "cmp_1",
    "slug": "gsoc-update",
    "title": "GSoC Update",
    "subject": "GSoC Update",
    "summary": "Short summary",
    "status": "draft",
    "markdown_body": "## Shipped",
    "html_body": "",
    "scheduled_for": "",
    "published_at": "",
    "sent_at": "",
    "created_by_admin_id": "adm_1",
    "created_at": "2026-06-21T00:00:00Z",
    "updated_at": "2026-06-21T00:00:00Z",
    "metadata_json": "{}",
}


class CampaignModelTests(unittest.TestCase):
    def test_worker_exposes_campaign_routes_and_not_issue_routes(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        for expected in [
            '"/api/admin/campaigns"',
            '"/api/campaigns"',
            "handle_admin_campaigns",
            "handle_admin_create_campaign",
            "handle_admin_patch_campaign",
            "handle_admin_publish_campaign",
            "handle_public_campaigns",
            "handle_public_campaign_detail",
        ]:
            self.assertIn(expected, entrypoint)

        self.assertNotIn('"/api/admin/issues"', entrypoint)
        self.assertNotIn('"/api/issues"', entrypoint)
        self.assertNotIn("handle_admin_create_issue", entrypoint)
        self.assertNotIn("handle_admin_send_issue", entrypoint)

    def test_migration_declares_campaign_table_and_campaign_send_jobs(self):
        migration = (ROOT / "migrations" / "0001_newsletter_schema.sql").read_text()

        self.assertIn("CREATE TABLE IF NOT EXISTS newsletter_campaigns", migration)
        self.assertIn("campaign_id TEXT NOT NULL", migration)
        self.assertIn("FOREIGN KEY (campaign_id) REFERENCES newsletter_campaigns (id)", migration)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS newsletter_issues", migration)
        self.assertNotIn("issue_id TEXT NOT NULL", migration)

    def test_campaign_schema_supports_current_and_legacy_local_columns(self):
        self.assertEqual(campaign_slug_column(CAMPAIGN_COLUMNS), "slug")
        self.assertIn("slug", campaign_select_columns(CAMPAIGN_COLUMNS))
        self.assertIn("summary", campaign_select_columns(CAMPAIGN_COLUMNS))
        self.assertIn("published_at", campaign_select_columns(CAMPAIGN_COLUMNS))
        self.assertEqual(
            campaign_order_expression(CAMPAIGN_COLUMNS),
            "COALESCE(NULLIF(published_at, ''), created_at)",
        )

        legacy_select = campaign_select_columns(LEGACY_COLUMNS)
        self.assertEqual(campaign_slug_column(LEGACY_COLUMNS), "issue_slug")
        self.assertIn("issue_slug AS slug", legacy_select)
        self.assertIn("'' AS summary", legacy_select)
        self.assertIn("'' AS published_at", legacy_select)

    def test_campaign_insert_and_update_map_to_available_columns(self):
        columns, params = campaign_insert_columns_and_params(CAMPAIGN_RECORD, CAMPAIGN_COLUMNS)
        legacy_columns, legacy_params = campaign_insert_columns_and_params(CAMPAIGN_RECORD, LEGACY_COLUMNS)

        self.assertIn("slug", columns)
        self.assertIn("summary", columns)
        self.assertIn("published_at", columns)
        self.assertIn("issue_slug", legacy_columns)
        self.assertNotIn("summary", legacy_columns)
        self.assertEqual(legacy_params[legacy_columns.index("issue_slug")], "gsoc-update")

        updates = {
            "slug": "new-slug",
            "summary": "New summary",
            "status": "published",
            "published_at": "2026-06-21T00:00:00Z",
            "updated_at": "2026-06-21T00:00:00Z",
        }
        current_updates = map_campaign_update_fields(updates, CAMPAIGN_COLUMNS)
        legacy_updates = map_campaign_update_fields(updates, LEGACY_COLUMNS)

        self.assertEqual(current_updates["slug"], "new-slug")
        self.assertEqual(current_updates["summary"], "New summary")
        self.assertEqual(legacy_updates["issue_slug"], "new-slug")
        self.assertNotIn("summary", legacy_updates)

    def test_send_job_schema_prefers_campaign_id_with_legacy_issue_id_fallback(self):
        self.assertEqual(send_job_campaign_column(["id", "campaign_id", "status"]), "campaign_id")
        self.assertEqual(send_job_campaign_column(["id", "issue_id", "status"]), "issue_id")

    def test_dashboard_is_campaign_first_and_uses_publish_action(self):
        page = (ROOT / "public" / "dashboard.html").read_text()

        for expected in [
            "campaigns-page",
            "campaign-title",
            "campaign-slug",
            "campaign-subject",
            "campaign-summary",
            "campaign-markdown-body",
            "campaigns-table-body",
            "async function saveCampaignDraft()",
            "async function publishCampaign()",
            'adminFetch("/api/admin/campaigns", {',
            "/publish`, {",
        ]:
            self.assertIn(expected, page)

        for removed in [
            "New issue",
            "Issues",
            "issues-page",
            "issue-title",
            "issue-slug",
            "issue-subject",
            "issue-summary",
            "issue-markdown-body",
            "/api/admin/issues",
            "data-issue-id",
        ]:
            self.assertNotIn(removed, page)


if __name__ == "__main__":
    unittest.main()
