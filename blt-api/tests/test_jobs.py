import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


from handlers.jobs import handle_jobs


class MockRequest:
    def __init__(self, method="GET", body=None, user_id=None):
        self.method = method
        self._body = body
        if user_id is not None:
            self.user_id = user_id

    async def text(self):
        if self._body is None:
            return ""
        if isinstance(self._body, dict):
            return json.dumps(self._body)
        return str(self._body)


class MockEnv:
    pass


def _json(response):
    return json.loads(response.body)


def _job_queryset(rows=None, row=None, count=0):
    qs = MagicMock()
    qs.filter.return_value = qs
    qs.order_by.return_value = qs
    qs.paginate.return_value = qs
    qs.all = AsyncMock(return_value=rows or [])
    qs.first = AsyncMock(return_value=row)
    qs.get = AsyncMock(return_value=row)
    qs.count = AsyncMock(return_value=count)
    qs.update = AsyncMock()
    return qs


@pytest.mark.asyncio
async def test_jobs_list_requires_user_api_key_context():
    with patch("handlers.jobs.get_db_safe", AsyncMock(return_value=MagicMock())):
        response = await handle_jobs(MockRequest(), MockEnv(), {}, {}, "/v2/jobs")

    assert response.status == 401
    assert _json(response)["message"] == "User API key required"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path_params", "body", "path"),
    [
        ("GET", {}, None, "/v2/jobs"),
        ("GET", {"id": "5"}, None, "/v2/jobs/5"),
        ("GET", {}, None, "/v2/jobs/stats"),
        (
            "POST",
            {},
            {"title": "Security Engineer", "description": "Work on BLT integrations."},
            "/v2/jobs",
        ),
        ("PATCH", {"id": "5"}, {"status": "closed"}, "/v2/jobs/5"),
        ("POST", {"id": "5"}, None, "/v2/jobs/5/view"),
    ],
)
async def test_jobs_routes_require_user_api_key_context(method, path_params, body, path):
    response = await handle_jobs(
        MockRequest(method=method, body=body),
        MockEnv(),
        path_params,
        {},
        path,
    )

    assert response.status == 401
    assert _json(response)["message"] == "User API key required"


@pytest.mark.asyncio
async def test_jobs_list_returns_only_current_users_jobs():
    qs = _job_queryset(
        rows=[{"id": 1, "title": "AppSec Engineer", "created_by_user_id": 42}],
        count=1,
    )
    job_model = MagicMock()
    job_model.objects.return_value = qs

    with patch("handlers.jobs.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.jobs.Job", job_model):
        response = await handle_jobs(
            MockRequest(user_id=42),
            MockEnv(),
            {},
            {"page": "1", "per_page": "20"},
            "/v2/jobs",
        )

    assert response.status == 200
    data = _json(response)
    assert data["data"] == [{"id": 1, "title": "AppSec Engineer", "created_by_user_id": 42}]
    qs.filter.assert_any_call(created_by_user_id=42)


@pytest.mark.asyncio
async def test_jobs_create_sets_current_user_owner():
    created_job = {"id": 9, "title": "Security Engineer", "created_by_user_id": 42}
    job_model = MagicMock()
    job_model.create = AsyncMock(return_value=created_job)

    body = {
        "title": "Security Engineer",
        "description": "Work on BLT integrations.",
        "company_name": "OWASP BLT",
    }

    with patch("handlers.jobs.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.jobs.Job", job_model):
        response = await handle_jobs(
            MockRequest(method="POST", body=body, user_id=42),
            MockEnv(),
            {},
            {},
            "/v2/jobs",
        )

    assert response.status == 201
    job_model.create.assert_awaited_once()
    create_kwargs = job_model.create.await_args.kwargs
    assert create_kwargs["created_by_user_id"] == 42
    assert create_kwargs["title"] == "Security Engineer"
    assert _json(response)["data"] == created_job


@pytest.mark.asyncio
async def test_jobs_detail_returns_owned_job():
    job = {"id": 5, "title": "Security Engineer", "created_by_user_id": 42}
    qs = _job_queryset(row=job)
    job_model = MagicMock()
    job_model.objects.return_value = qs

    with patch("handlers.jobs.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.jobs.Job", job_model):
        response = await handle_jobs(
            MockRequest(user_id=42),
            MockEnv(),
            {"id": "5"},
            {},
            "/v2/jobs/5",
        )

    assert response.status == 200
    assert _json(response)["data"] == job
    qs.get.assert_awaited_once_with(id=5, created_by_user_id=42)


@pytest.mark.asyncio
async def test_jobs_update_changes_owned_job():
    existing = {"id": 5, "title": "Security Engineer", "status": "open", "created_by_user_id": 42}
    updated = dict(existing, status="closed")
    qs = _job_queryset()
    qs.get = AsyncMock(side_effect=[existing, updated])
    job_model = MagicMock()
    job_model.objects.return_value = qs

    with patch("handlers.jobs.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.jobs.Job", job_model):
        response = await handle_jobs(
            MockRequest(method="PATCH", body={"status": "closed"}, user_id=42),
            MockEnv(),
            {"id": "5"},
            {},
            "/v2/jobs/5",
        )

    assert response.status == 200
    qs.update.assert_awaited_once_with(status="closed")
    assert _json(response)["data"]["status"] == "closed"


@pytest.mark.asyncio
async def test_jobs_update_denies_jobs_owned_by_another_user():
    qs = _job_queryset(row=None)
    job_model = MagicMock()
    job_model.objects.return_value = qs

    with patch("handlers.jobs.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.jobs.Job", job_model):
        response = await handle_jobs(
            MockRequest(method="PATCH", body={"status": "closed"}, user_id=42),
            MockEnv(),
            {"id": "5"},
            {},
            "/v2/jobs/5",
        )

    assert response.status == 404
    qs.get.assert_awaited_once_with(id=5, created_by_user_id=42)


@pytest.mark.asyncio
async def test_jobs_view_increments_current_users_job():
    qs = _job_queryset(row={"id": 5, "views": 2, "created_by_user_id": 42})
    job_model = MagicMock()
    job_model.objects.return_value = qs

    with patch("handlers.jobs.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.jobs.Job", job_model):
        response = await handle_jobs(
            MockRequest(method="POST", user_id=42),
            MockEnv(),
            {"id": "5"},
            {},
            "/v2/jobs/5/view",
        )

    assert response.status == 200
    qs.update.assert_awaited_once_with(views=3)
    assert _json(response)["data"]["views"] == 3


@pytest.mark.asyncio
async def test_jobs_stats_returns_current_users_counts():
    job_model = MagicMock()
    querysets = [
        _job_queryset(count=12),
        _job_queryset(count=10),
        _job_queryset(count=8),
        _job_queryset(count=4),
    ]
    job_model.objects.side_effect = querysets

    with patch("handlers.jobs.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.jobs.Job", job_model):
        response = await handle_jobs(
            MockRequest(user_id=42),
            MockEnv(),
            {},
            {},
            "/v2/jobs/stats",
        )

    assert response.status == 200
    assert _json(response)["data"] == {
        "total_jobs": 12,
        "active_jobs": 10,
        "open_jobs": 8,
        "closed_jobs": 4,
    }
