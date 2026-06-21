import unittest

from src.newsletter_issue_schema import (
    issue_insert_columns_and_params,
    issue_order_expression,
    issue_select_columns,
    issue_slug_column,
    map_issue_update_fields,
)


CURRENT_COLUMNS = [
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

STALE_COLUMNS = [
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

ISSUE_RECORD = {
    "id": "issue_1",
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


class IssueSchemaCompatibilityTests(unittest.TestCase):
    def test_current_issue_schema_uses_slug_summary_and_published_at_columns(self):
        self.assertEqual(issue_slug_column(CURRENT_COLUMNS), "slug")
        self.assertIn("slug", issue_select_columns(CURRENT_COLUMNS))
        self.assertIn("summary", issue_select_columns(CURRENT_COLUMNS))
        self.assertIn("published_at", issue_select_columns(CURRENT_COLUMNS))
        self.assertEqual(issue_order_expression(CURRENT_COLUMNS), "COALESCE(NULLIF(published_at, ''), created_at)")

    def test_stale_issue_schema_projects_issue_slug_and_missing_optional_fields(self):
        select_columns = issue_select_columns(STALE_COLUMNS)

        self.assertEqual(issue_slug_column(STALE_COLUMNS), "issue_slug")
        self.assertIn("issue_slug AS slug", select_columns)
        self.assertIn("'' AS summary", select_columns)
        self.assertIn("'' AS published_at", select_columns)
        self.assertEqual(issue_order_expression(STALE_COLUMNS), "created_at")

    def test_issue_insert_maps_record_to_current_schema(self):
        columns, params = issue_insert_columns_and_params(ISSUE_RECORD, CURRENT_COLUMNS)

        self.assertIn("slug", columns)
        self.assertIn("summary", columns)
        self.assertIn("published_at", columns)
        self.assertNotIn("issue_slug", columns)
        self.assertEqual(params[columns.index("slug")], "gsoc-update")
        self.assertEqual(params[columns.index("summary")], "Short summary")

    def test_issue_insert_maps_record_to_stale_schema_without_missing_columns(self):
        columns, params = issue_insert_columns_and_params(ISSUE_RECORD, STALE_COLUMNS)

        self.assertIn("issue_slug", columns)
        self.assertNotIn("slug", columns)
        self.assertNotIn("summary", columns)
        self.assertNotIn("published_at", columns)
        self.assertEqual(params[columns.index("issue_slug")], "gsoc-update")
        self.assertEqual(len(columns), len(params))

    def test_issue_updates_map_slug_and_skip_missing_optional_columns(self):
        updates = {
            "slug": "new-slug",
            "summary": "New summary",
            "status": "published",
            "published_at": "2026-06-21T00:00:00Z",
            "updated_at": "2026-06-21T00:00:00Z",
        }

        current_updates = map_issue_update_fields(updates, CURRENT_COLUMNS)
        stale_updates = map_issue_update_fields(updates, STALE_COLUMNS)

        self.assertEqual(current_updates["slug"], "new-slug")
        self.assertEqual(current_updates["summary"], "New summary")
        self.assertEqual(current_updates["published_at"], "2026-06-21T00:00:00Z")
        self.assertEqual(stale_updates["issue_slug"], "new-slug")
        self.assertNotIn("slug", stale_updates)
        self.assertNotIn("summary", stale_updates)
        self.assertNotIn("published_at", stale_updates)
        self.assertEqual(stale_updates["status"], "published")
        self.assertEqual(stale_updates["updated_at"], "2026-06-21T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
