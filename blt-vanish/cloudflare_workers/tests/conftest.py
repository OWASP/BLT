import sys
import types
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))


class FakeResponse:
    def __init__(self, body="", status=200, headers=None):
        self.body = body
        self.text = body
        self.status = status
        self.headers = dict(headers or {})


class FakeWorkerEntrypoint:
    pass


class FakeAbortSignal:
    @staticmethod
    def timeout(_milliseconds):
        return None


async def fake_fetch(*_args, **_kwargs):
    return FakeResponse(status=202)


workers = types.ModuleType("workers")
workers.Response = FakeResponse
workers.WorkerEntrypoint = FakeWorkerEntrypoint
workers.fetch = fake_fetch
sys.modules["workers"] = workers

js = types.ModuleType("js")
js.AbortSignal = FakeAbortSignal
sys.modules["js"] = js


@pytest.fixture(autouse=True)
def reset_rate_limits():
    import middleware

    middleware._ip_requests.clear()
