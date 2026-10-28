import asyncio
import json
import types
from unittest.mock import AsyncMock

from test_cron_dispatch import _load_worker


class FakeKV:
    def __init__(self, data=None):
        self.data = {} if data is None else data

    async def get(self, key):
        return self.data.get(key)

    async def put(self, key, value):
        self.data[key] = value


class FakeResponse:
    def __init__(self, text, ok=True, status=200):
        self._text = text
        self.ok = ok
        self.status = status

    async def text(self):
        return self._text


def _env(token="token", history=None):
    env = types.SimpleNamespace(INGEST_TOKEN=token)
    setattr(env, "blt-monitor-history", FakeKV(history))
    return env


def test_append_history_rejects_invalid_status_or_negative_duration():
    worker = _load_worker()
    entry = worker.Default(env=_env())

    for payload, expected_error in [
        ({"datetime": "2026-01-01T00:00:00Z", "duration_ms": -1, "status": "success", "keyword_status": "found"}, "Invalid duration"),
        ({"datetime": "2026-01-01T00:00:00Z", "duration_ms": 25, "status": "unknown", "keyword_status": "found"}, "Invalid status"),
    ]:
        request = types.SimpleNamespace(
            headers={"Authorization": "Bearer token"},
            text=AsyncMock(return_value=json.dumps(payload)),
        )
        response = asyncio.run(entry.append_history(request, "site"))
        assert response.status == 400
        assert json.loads(response.body)["error"] == expected_error


def test_add_history_entry_keeps_last_30_entries():
    worker = _load_worker()
    histories = {"site": [{"n": i} for i in range(30)]}

    history = worker.Default.add_history_entry(histories, "site", {"n": 30})

    assert len(history) == 30
    assert history[0] == {"n": 1}
    assert history[-1] == {"n": 30}


def test_load_histories_returns_empty_dict_for_corrupt_json():
    worker = _load_worker()
    env = _env(history={"histories:0": "{not valid json"})

    histories = asyncio.run(worker.Default(env).load_histories(0, env))

    assert histories == {}


def test_check_monitor_marks_missing_keyword_as_failure_on_200():
    worker = _load_worker()
    worker.fetch = AsyncMock(return_value=FakeResponse("nothing useful here", ok=True))
    monitor = {"id": "site", "url": "https://site.example", "keyword": "expected"}

    result = asyncio.run(worker.Default(env=types.SimpleNamespace()).check_monitor(monitor))

    assert result["status"] == "failure"
    assert result["keyword_status"] == "not_found"


def test_check_monitor_accepts_cloudflare_captcha_as_success():
    worker = _load_worker()
    worker.fetch = AsyncMock(
        return_value=FakeResponse(
            "verify you are human by completing the action below",
            ok=True,
        )
    )
    monitor = {"id": "captcha", "url": "https://site.example", "keyword": "expected"}

    result = asyncio.run(worker.Default(env=types.SimpleNamespace()).check_monitor(monitor))

    assert result["status"] == "success"
    assert result["keyword_status"] == "not_found"


def test_monitor_shard_is_stable_and_bounded():
    worker = _load_worker()
    shard = worker.Default.monitor_shard("example-site")

    assert isinstance(shard, int)
    assert 0 <= shard < worker.HISTORY_SHARDS
    assert shard == worker.Default.monitor_shard("example-site")
