import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "workers" / "main.py"


class TestOrganizationRoutesContract(unittest.TestCase):
    def setUp(self):
        self.source = MAIN.read_text()
        self.normalized = re.sub(r"\s+", " ", self.source)

    def test_generic_org_routes_are_registered(self):
        for route in [
            '"/api/orgs/discover"',
            '"/api/orgs" and method == "POST"',
            '"/api/orgs" and method == "GET"',
            'api_path.endswith("/join") and method == "POST"',
            'api_path.endswith("/requests") and method == "GET"',
            'api_path.endswith("/role") and method == "POST"',
        ]:
            self.assertIn(route, self.source)
        for handler in [
            "handle_discover_orgs",
            "handle_add_org",
            "handle_join_org",
            "handle_get_org_requests",
            "handle_update_org_member_role",
        ]:
            self.assertIn(handler, self.source)

    def test_org_helpers_slugify_and_require_verified_users(self):
        for helper in ["slugify_org", "get_verified_session_user", "get_org_by_slug", "require_org_admin"]:
            self.assertIn(f"def {helper}", self.source)
        self.assertIn("email_verified", self.source)
        self.assertIn("Email verification required", self.source)
        self.assertIn("^[a-z0-9]+(?:-[a-z0-9]+)*$", self.source)

    def test_create_org_sets_creator_as_owner_approved(self):
        start = self.source.index("async def handle_add_org")
        end = self.source.index("async def handle_join_org")
        body = self.source[start:end]
        self.assertIn("get_verified_session_user", body)
        self.assertIn("slugify_org", body)
        self.assertIn("INSERT INTO organizations", body)
        self.assertIn("created_by_user_id", body)
        self.assertIn("INSERT INTO user_organizations", body)
        self.assertIn("'approved'", body)
        self.assertIn("'owner'", body)
        self.assertNotIn("GitHub membership", body)

    def test_join_org_creates_pending_member_request(self):
        start = self.source.index("async def handle_join_org")
        end = self.source.index("async def handle_get_org_requests")
        body = self.source[start:end]
        self.assertIn("get_verified_session_user", body)
        self.assertIn("get_org_by_slug", body)
        self.assertIn("INSERT INTO user_organizations", body)
        self.assertIn("'pending'", body)
        self.assertIn("'member'", body)
        self.assertIn("requested_at", body)

    def test_admin_routes_require_owner_or_admin_and_update_role_status(self):
        for name in ["handle_get_org_requests", "handle_approve_org_member", "handle_deny_org_member", "handle_update_org_member_role"]:
            start = self.source.index(f"async def {name}")
            # Use a bounded slice to avoid depending on full file order.
            body = self.source[start:start + 2400]
            self.assertIn("require_org_admin", body, name)
        self.assertIn("approved_by_user_id", self.source)
        self.assertIn("approved_at", self.source)
        self.assertIn("role = ?", self.source)
        self.assertIn("Cannot remove the last owner", self.source)

    def test_org_discovery_returns_membership_and_role_shape(self):
        start = self.source.index("async def handle_discover_orgs")
        end = self.source.index("async def handle_get_orgs")
        body = self.source[start:end] + self.source[self.source.index("def org_row_to_api"):self.source.index("async def handle_discover_orgs")]
        for key in ['"slug"', '"name"', '"description"', '"membershipStatus"', '"role"', '"checkinEnabled"']:
            self.assertIn(key, body)
        self.assertIn("LEFT JOIN user_organizations", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
