import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


from handlers.hackathons import handle_hackathons


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
    USER_DATA_HASH_KEY = "hash-key"
    USER_DATA_ENCRYPTION_KEY = "encryption-key"


def _json(response):
    return json.loads(response.body)


def _queryset(rows=None, row=None, count=0):
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
async def test_hackathons_list_requires_user_api_key_context():
    with patch("handlers.hackathons.get_db_safe", AsyncMock(return_value=MagicMock())):
        response = await handle_hackathons(MockRequest(), MockEnv(), {}, {}, "/v2/hackathons")

    assert response.status == 401
    assert _json(response)["message"] == "User API key required"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path_params", "body", "path"),
    [
        ("GET", {}, None, "/v2/hackathons"),
        ("GET", {"slug": "blt-build-day"}, None, "/v2/hackathons/blt-build-day"),
        (
            "POST",
            {},
            {
                "title": "BLT Build Day",
                "slug": "blt-build-day",
                "starts_at": "2026-07-01 00:00:00",
                "ends_at": "2026-07-03 00:00:00",
            },
            "/v2/hackathons",
        ),
        ("PATCH", {"id": "7"}, {"capacity": 100}, "/v2/hackathons/7"),
        (
            "POST",
            {"id": "7"},
            {"email": "participant@example.com"},
            "/v2/hackathons/7/register",
        ),
    ],
)
async def test_hackathons_routes_require_user_api_key_context(method, path_params, body, path):
    response = await handle_hackathons(
        MockRequest(method=method, body=body),
        MockEnv(),
        path_params,
        {},
        path,
    )

    assert response.status == 401
    assert _json(response)["message"] == "User API key required"


@pytest.mark.asyncio
async def test_hackathons_list_scopes_to_current_user_and_computes_status():
    rows = [
        {
            "id": 1,
            "title": "BLT Build Day",
            "slug": "blt-build-day",
            "starts_at": "2026-06-10 00:00:00",
            "ends_at": "2026-06-12 00:00:00",
            "created_by_user_id": 42,
        }
    ]
    qs = _queryset(rows=rows, count=1)
    hackathon_model = MagicMock()
    hackathon_model.objects.return_value = qs

    with patch("handlers.hackathons.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.hackathons.Hackathon", hackathon_model), \
         patch("handlers.hackathons._utc_now", return_value="2026-06-11 00:00:00"):
        response = await handle_hackathons(
            MockRequest(user_id=42),
            MockEnv(),
            {},
            {"page": "1", "per_page": "20"},
            "/v2/hackathons",
        )

    assert response.status == 200
    data = _json(response)
    assert data["data"][0]["status"] == "ongoing"
    qs.filter.assert_any_call(created_by_user_id=42)


@pytest.mark.asyncio
async def test_hackathons_create_sets_current_user_owner():
    created = {"id": 3, "slug": "summer-bugs", "created_by_user_id": 42}
    hackathon_model = MagicMock()
    hackathon_model.create = AsyncMock(return_value=created)

    body = {
        "title": "Summer Bugs",
        "slug": "summer-bugs",
        "starts_at": "2026-07-01 00:00:00",
        "ends_at": "2026-07-03 00:00:00",
        "capacity": 100,
    }

    with patch("handlers.hackathons.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.hackathons.Hackathon", hackathon_model):
        response = await handle_hackathons(
            MockRequest(method="POST", body=body, user_id=42),
            MockEnv(),
            {},
            {},
            "/v2/hackathons",
        )

    assert response.status == 201
    create_kwargs = hackathon_model.create.await_args.kwargs
    assert create_kwargs["created_by_user_id"] == 42
    assert create_kwargs["slug"] == "summer-bugs"
    assert _json(response)["data"] == created


@pytest.mark.asyncio
async def test_hackathons_create_duplicate_slug_returns_409_not_500():
    hackathon_model = MagicMock()
    hackathon_model.create = AsyncMock(
        side_effect=Exception(
            "D1_ERROR: UNIQUE constraint failed: hackathons.created_by_user_id, hackathons.slug: SQLITE_CONSTRAINT"
        )
    )

    body = {
        "title": "BLT Build Day",
        "slug": "blt-build-day",
        "starts_at": "2026-07-01 00:00:00",
        "ends_at": "2026-07-03 00:00:00",
    }

    with patch("handlers.hackathons.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.hackathons.Hackathon", hackathon_model):
        response = await handle_hackathons(
            MockRequest(method="POST", body=body, user_id=42),
            MockEnv(),
            {},
            {},
            "/v2/hackathons",
        )

    assert response.status == 409
    assert "slug" in _json(response)["message"].lower()


@pytest.mark.asyncio
async def test_hackathons_detail_returns_owned_hackathon_by_slug():
    hackathon = {
        "id": 7,
        "title": "BLT Build Day",
        "slug": "blt-build-day",
        "starts_at": "2026-06-10 00:00:00",
        "ends_at": "2026-06-12 00:00:00",
        "created_by_user_id": 42,
    }
    hackathon_qs = _queryset(row=hackathon)
    registration_qs = _queryset(count=3)
    hackathon_model = MagicMock()
    registration_model = MagicMock()
    hackathon_model.objects.return_value = hackathon_qs
    registration_model.objects.return_value = registration_qs

    with patch("handlers.hackathons.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.hackathons.Hackathon", hackathon_model), \
         patch("handlers.hackathons.HackathonRegistration", registration_model), \
         patch("handlers.hackathons._utc_now", return_value="2026-06-11 00:00:00"):
        response = await handle_hackathons(
            MockRequest(user_id=42),
            MockEnv(),
            {"slug": "blt-build-day"},
            {},
            "/v2/hackathons/blt-build-day",
        )

    assert response.status == 200
    data = _json(response)["data"]
    assert data["status"] == "ongoing"
    assert data["registration_count"] == 3
    hackathon_qs.get.assert_awaited_once_with(slug="blt-build-day", created_by_user_id=42)


@pytest.mark.asyncio
async def test_hackathons_patch_updates_owned_hackathon():
    existing = {
        "id": 7,
        "title": "BLT Build Day",
        "slug": "blt-build-day",
        "starts_at": "2026-06-10 00:00:00",
        "ends_at": "2026-06-12 00:00:00",
        "capacity": 100,
        "created_by_user_id": 42,
    }
    updated = dict(existing, capacity=150)
    qs = _queryset()
    qs.get = AsyncMock(side_effect=[existing, updated])
    hackathon_model = MagicMock()
    hackathon_model.objects.return_value = qs

    with patch("handlers.hackathons.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.hackathons.Hackathon", hackathon_model):
        response = await handle_hackathons(
            MockRequest(method="PATCH", body={"capacity": 150}, user_id=42),
            MockEnv(),
            {"id": "7"},
            {},
            "/v2/hackathons/7",
        )

    assert response.status == 200
    qs.update.assert_awaited_once_with(capacity=150)
    assert _json(response)["data"]["capacity"] == 150


@pytest.mark.asyncio
async def test_hackathon_register_rejects_duplicate_email():
    hackathon = {"id": 7, "capacity": 10, "created_by_user_id": 42}
    hackathon_qs = _queryset(row=hackathon)
    registration_qs = _queryset(row={"id": 1})
    hackathon_model = MagicMock()
    registration_model = MagicMock()
    hackathon_model.objects.return_value = hackathon_qs
    registration_model.objects.return_value = registration_qs

    with patch("handlers.hackathons.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.hackathons.Hackathon", hackathon_model), \
         patch("handlers.hackathons.HackathonRegistration", registration_model), \
         patch("handlers.hackathons.blind_index", return_value="email-hash"):
        response = await handle_hackathons(
            MockRequest(
                method="POST",
                body={"email": "user@example.com", "name": "User"},
                user_id=42,
            ),
            MockEnv(),
            {"id": "7"},
            {},
            "/v2/hackathons/7/register",
        )

    assert response.status == 409
    assert "already registered" in _json(response)["message"].lower()


@pytest.mark.asyncio
async def test_hackathon_register_rejects_full_capacity():
    hackathon = {"id": 7, "capacity": 1, "created_by_user_id": 42}
    hackathon_qs = _queryset(row=hackathon)
    duplicate_qs = _queryset(row=None)
    capacity_qs = _queryset(count=1)
    hackathon_model = MagicMock()
    registration_model = MagicMock()
    hackathon_model.objects.return_value = hackathon_qs
    registration_model.objects.side_effect = [duplicate_qs, capacity_qs]

    with patch("handlers.hackathons.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.hackathons.Hackathon", hackathon_model), \
         patch("handlers.hackathons.HackathonRegistration", registration_model), \
         patch("handlers.hackathons.blind_index", return_value="email-hash"):
        response = await handle_hackathons(
            MockRequest(method="POST", body={"email": "user@example.com"}, user_id=42),
            MockEnv(),
            {"id": "7"},
            {},
            "/v2/hackathons/7/register",
        )

    assert response.status == 409
    assert "capacity" in _json(response)["message"].lower()


@pytest.mark.asyncio
async def test_hackathon_register_success_hides_email_storage_fields():
    hackathon = {"id": 7, "capacity": 10, "created_by_user_id": 42}
    hackathon_qs = _queryset(row=hackathon)
    duplicate_qs = _queryset(row=None)
    capacity_qs = _queryset(count=0)
    created_registration = {
        "id": 11,
        "hackathon_id": 7,
        "participant_name": "Participant",
        "participant_email_encrypted": "secret",
        "participant_email_hash": "hash",
        "status": "registered",
    }
    hackathon_model = MagicMock()
    registration_model = MagicMock()
    hackathon_model.objects.return_value = hackathon_qs
    registration_model.objects.side_effect = [duplicate_qs, capacity_qs]
    registration_model.create = AsyncMock(return_value=created_registration)

    with patch("handlers.hackathons.get_db_safe", AsyncMock(return_value=MagicMock())), \
         patch("handlers.hackathons.Hackathon", hackathon_model), \
         patch("handlers.hackathons.HackathonRegistration", registration_model), \
         patch("handlers.hackathons.blind_index", return_value="email-hash"), \
         patch("handlers.hackathons.encrypt_sensitive", return_value="encrypted-email"):
        response = await handle_hackathons(
            MockRequest(
                method="POST",
                body={"email": "participant@example.com", "name": "Participant"},
                user_id=42,
            ),
            MockEnv(),
            {"id": "7"},
            {},
            "/v2/hackathons/7/register",
        )

    assert response.status == 201
    data = _json(response)["data"]
    assert data["participant_name"] == "Participant"
    assert "participant_email_encrypted" not in data
    assert "participant_email_hash" not in data
