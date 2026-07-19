"""Production edge-case integration tests.

Covers restart recovery, cursor persistence, duplicate across
ingestion paths, and health endpoint richness.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from httpx import AsyncClient

from src.storage import CursorQueries, EventQueries
from tests.integration.conftest import insert_event, insert_contributor


class TestCursorPersistenceAcrossRestarts:
    """Cursors survive DB close/reopen cycles."""

    async def test_cursor_persists(self, db):
        """A cursor written is readable after a simulated restart."""
        await CursorQueries(db).upsert("gitlab_events_24246165", 99)

        # Simulate restart: close + reconnect
        await db.close()
        await db.connect()

        cursor = await CursorQueries(db).get("gitlab_events_24246165")
        assert cursor is not None
        assert cursor[0] == 99

    async def test_cursor_partial_update(self, db):
        """Cursors for one project don't affect others."""
        await CursorQueries(db).upsert("gitlab_events_1", 10)
        await CursorQueries(db).upsert("gitlab_events_2", 20)

        c1 = await CursorQueries(db).get("gitlab_events_1")
        c2 = await CursorQueries(db).get("gitlab_events_2")
        assert c1[0] == 10
        assert c2[0] == 20


class TestDuplicateAcrossIngestionPaths:
    """Webhook and gap detector can produce the same event — idempotency wins."""

    async def test_webhook_and_direct_insert_duplicate(self, client: AsyncClient, db):
        """Inserting the same event via webhook then directly does not duplicate."""
        payload = {
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "open",
                "title": "Dupe test",
                "state": "opened",
                "iid": 1,
                "created_at": "2026-06-30T10:00:00Z",
            },
            "user": {"id": 1, "username": "test"},
            "project": {"path_with_namespace": "owasp/blt"},
        }

        await client.post(
            "/webhook/gitlab",
            json=payload,
            headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Merge Request Hook"},
        )
        await asyncio.sleep(0.2)

        # Simulate gap detector normalizing the same payload
        from src.normalization.gitlab import normalize_gitlab_payload
        from src.storage import EventQueries
        event = normalize_gitlab_payload(payload)

        # Direct insert (same idempotency key) should be deduplicated
        inserted = await EventQueries(db).insert(event)
        assert inserted is False

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total == 1

    async def test_two_webhooks_same_payload(self, client: AsyncClient, db):
        """Two identical webhooks = one event."""
        payload = {
            "object_kind": "issue",
            "object_attributes": {
                "action": "open",
                "title": "Double post",
                "state": "opened",
                "iid": 2,
                "created_at": "2026-06-30T10:00:00Z",
            },
            "user": {"id": 2, "username": "doubleuser"},
            "project": {"path_with_namespace": "owasp/blt"},
        }

        r1 = await client.post(
            "/webhook/gitlab",
            json=payload,
            headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Issue Hook"},
        )
        r2 = await client.post(
            "/webhook/gitlab",
            json=payload,
            headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Issue Hook"},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200

        await asyncio.sleep(0.2)

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total == 1


class TestHealthEndpointRichness:
    """Health endpoint reports gaps and per-component state."""

    async def test_health_reports_disabled_webhook(self, client: AsyncClient, db):
        """If GITLAB_WEBHOOK_SECRET is set, webhook component is 'healthy'."""
        response = await client.get("/health")
        comp = response.json()["components"]["gitlab_webhook"]
        assert comp["status"] == "healthy"

    async def test_health_reports_gap_detector_disabled(self, client: AsyncClient):
        """Test app has no gap detector — reports disabled."""
        response = await client.get("/health")
        comp = response.json()["components"]["gitlab_gap_detector"]
        assert comp["status"] == "disabled"

    async def test_health_reports_blt_poller_disabled(self, client: AsyncClient):
        """Test app has no BLT poller — reports disabled."""
        response = await client.get("/health")
        comp = response.json()["components"]["blt_polling"]
        assert comp["status"] == "disabled"

    async def test_health_includes_webhook_last_event(self, client: AsyncClient):
        """After a webhook, health reflects last_event_at."""
        payload = {
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "open",
                "title": "Health test",
                "state": "opened",
                "iid": 3,
                "created_at": "2026-06-30T10:00:00Z",
            },
            "user": {"id": 3, "username": "healthcheck"},
            "project": {"path_with_namespace": "owasp/blt"},
        }

        await client.post(
            "/webhook/gitlab",
            json=payload,
            headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Merge Request Hook"},
        )
        await asyncio.sleep(0.2)

        response = await client.get("/health")
        webhook_comp = response.json()["components"]["gitlab_webhook"]
        assert webhook_comp["last_event_at"] is not None


class TestRestartRecovery:
    """Server restart leaves cursors and data intact."""

    async def test_events_persist_across_close_reopen(self, db):
        """Events survive DB close/reopen."""
        e1 = await insert_event(db, event_type="mr_opened")
        await insert_event(db, event_type="mr_merged")

        await db.close()
        await db.connect()

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total == 2

    async def test_contributors_persist(self, db):
        """Contributors survive DB restart."""
        c = await insert_contributor(db, score=99)

        await db.close()
        await db.connect()

        from src.storage import ContributorQueries
        restored = await ContributorQueries(db).get(c.id)
        assert restored is not None
        assert restored.score == 99


class TestEventOrdering:
    """Events are ordered correctly by timestamp then sequence."""

    async def test_events_ordered_with_same_timestamp(self, client: AsyncClient, db):
        """Events with the same timestamp use sequence numbers to break ties."""
        ts = datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
        # Use webhook path so sequence numbers are assigned
        for i in range(3):
            payload = {
                "object_kind": "merge_request",
                "object_attributes": {
                    "action": "open",
                    "title": f"Seq test {i}",
                    "state": "opened",
                    "iid": 100 + i,
                    "created_at": "2026-07-01T10:00:00Z",
                },
                "user": {"id": 100 + i, "username": f"sequser{i}"},
                "project": {"path_with_namespace": "owasp/blt"},
            }
            await client.post(
                "/webhook/gitlab",
                json=payload,
                headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Merge Request Hook"},
            )
            await asyncio.sleep(0.05)

        await asyncio.sleep(0.2)

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total == 3
        # Sequence numbers should increase
        seqs = [e.sequence_number for e in events if e.sequence_number is not None]
        assert seqs == sorted(seqs, reverse=True)


class TestPipelineErrors:
    """Events that fail normalization or processing are handled gracefully."""

    async def test_webhook_accepted_even_when_pipeline_busy(self, client: AsyncClient, db):
        """Sending many webhooks in rapid succession — all return 200."""
        payload = {
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "open",
                "title": "Burst test",
                "state": "opened",
                "iid": 500,
                "created_at": "2026-06-30T10:00:00Z",
            },
            "user": {"id": 500, "username": "burst"},
            "project": {"path_with_namespace": "owasp/blt"},
        }

        results = []
        for _ in range(5):
            r = await client.post(
                "/webhook/gitlab",
                json=payload,
                headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Merge Request Hook"},
            )
            results.append(r.status_code)

        assert all(s == 200 for s in results)
        await asyncio.sleep(0.3)

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total == 1  # Idempotent


class TestGitLabNormalizationVariants:
    """GitLab normalization handles various payload shapes."""

    async def test_webhook_pipeline_event(self, client: AsyncClient, db):
        """Pipeline Hook with success status."""
        payload = {
            "object_kind": "pipeline",
            "object_attributes": {
                "status": "success",
                "id": 123,
                "ref": "main",
                "created_at": "2026-06-30T10:00:00Z",
            },
            "user": {"id": 10, "username": "ci-bot"},
            "project": {"path_with_namespace": "owasp/blt"},
        }

        r = await client.post(
            "/webhook/gitlab",
            json=payload,
            headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Pipeline Hook"},
        )
        assert r.status_code == 200
        await asyncio.sleep(0.15)

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total >= 1
        assert events[0].event_type == "pipeline_run"

    async def test_webhook_note_event(self, client: AsyncClient, db):
        """Note Hook on an issue."""
        payload = {
            "object_kind": "note",
            "object_attributes": {
                "note": "LGTM",
                "url": "https://gitlab.com/owasp/blt/-/notes/1",
                "created_at": "2026-06-30T10:00:00Z",
            },
            "user": {"id": 11, "username": "reviewer"},
            "project": {"path_with_namespace": "owasp/blt"},
            "noteable_type": "Issue",
        }

        r = await client.post(
            "/webhook/gitlab",
            json=payload,
            headers={"X-Gitlab-Token": "s3cr3t", "X-Gitlab-Event": "Note Hook"},
        )
        assert r.status_code == 200
        await asyncio.sleep(0.15)

        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total >= 1
        assert events[0].event_type == "note_added"
