"""Integration tests for POST /webhook/gitlab (VF01)."""

from __future__ import annotations

import asyncio

from httpx import AsyncClient

from src.storage import EventQueries


GITLAB_MR_PAYLOAD = {
    "object_kind": "merge_request",
    "object_attributes": {
        "action": "open",
        "title": "Add awesome feature",
        "state": "opened",
        "source_branch": "feat/awesome",
        "target_branch": "main",
        "iid": 42,
        "created_at": "2026-06-24T10:00:00Z",
    },
    "user": {"id": 7, "username": "alice"},
    "project": {"path_with_namespace": "owasp/blt"},
}

GITLAB_ISSUE_PAYLOAD = {
    "object_kind": "issue",
    "object_attributes": {
        "action": "open",
        "title": "Bug: login broken",
        "state": "opened",
        "iid": 99,
        "created_at": "2026-06-24T10:00:00Z",
    },
    "user": {"id": 7, "username": "alice"},
    "project": {"path_with_namespace": "owasp/blt"},
}


class TestGitLabWebhookEndpoint:
    """GitLab webhook ingestion end-to-end."""

    async def test_webhook_accepted(self, client: AsyncClient):
        """Valid webhook returns 200."""
        response = await client.post(
            "/webhook/gitlab",
            json=GITLAB_MR_PAYLOAD,
            headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Merge Request Hook"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    async def test_webhook_invalid_token(self, client: AsyncClient):
        """Wrong token returns 401."""
        response = await client.post(
            "/webhook/gitlab",
            json=GITLAB_MR_PAYLOAD,
            headers={"X-Gitlab-Token": "wrong-secret"},
        )
        assert response.status_code == 401

    async def test_webhook_missing_token(self, client: AsyncClient):
        """Missing token header returns 401."""
        response = await client.post(
            "/webhook/gitlab",
            json=GITLAB_MR_PAYLOAD,
        )
        assert response.status_code == 401

    async def test_webhook_missing_event_header(self, client: AsyncClient):
        """Webhook works without X-Gitlab-Event header (falls back to object_kind)."""
        response = await client.post(
            "/webhook/gitlab",
            json=GITLAB_MR_PAYLOAD,
            headers={"X-Gitlab-Token": "s3cr3t"},
        )
        assert response.status_code == 200

    async def test_webhook_unknown_event_type(self, client: AsyncClient, db):
        """Unknown object_kind normalizes to event_type 'unknown' and returns 200."""
        import asyncio
        from src.storage import EventQueries

        response = await client.post(
            "/webhook/gitlab",
            json={"object_kind": "unknown", "user": {"id": 1, "username": "bot"}},
            headers={"X-Gitlab-Token": "s3cr3t"},
        )
        assert response.status_code == 200

        await asyncio.sleep(0.15)
        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total >= 1
        assert events[0].event_type == "unknown"

    async def test_webhook_persists_event(self, client: AsyncClient, db):
        """Accepted webhook results in a persisted event via pipeline."""
        response = await client.post(
            "/webhook/gitlab",
            json=GITLAB_MR_PAYLOAD,
            headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Merge Request Hook"},
        )
        assert response.status_code == 200

        await asyncio.sleep(0.15)

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total >= 1
        assert events[0].source == "gitlab"
        assert events[0].event_type == "mr_opened"
        assert events[0].actor_name == "alice"

    async def test_webhook_idempotent(self, client: AsyncClient, db):
        """Same webhook sent twice does not duplicate."""
        for _ in range(2):
            await client.post(
                "/webhook/gitlab",
                json=GITLAB_MR_PAYLOAD,
                headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Merge Request Hook"},
            )

        await asyncio.sleep(0.15)

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total == 1

    async def test_webhook_issue_event(self, client: AsyncClient, db):
        """Issue webhook is accepted and persisted."""
        response = await client.post(
            "/webhook/gitlab",
            json=GITLAB_ISSUE_PAYLOAD,
            headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Issue Hook"},
        )
        assert response.status_code == 200

        await asyncio.sleep(0.15)

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total >= 1
        assert events[0].event_type == "issue_opened"
