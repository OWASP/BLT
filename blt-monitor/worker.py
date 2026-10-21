import hmac
import json
import re
from datetime import datetime, timezone
from time import perf_counter
from urllib.parse import parse_qs, urlparse

from workers import Response, WorkerEntrypoint, fetch

MAX_HISTORY_ENTRIES = 30
HISTORY_BINDING = "blt-monitor-history"
HISTORY_SHARDS = 4
SHARD_INTERVAL_MS = 5 * 60 * 1000
MONITOR_ID_PATTERN = re.compile(r"^[a-z0-9_-]+$")

# Cron dispatch: the blt-cron Worker holds the account's cron trigger and calls
# POST /__scheduled through a service binding, authenticated with CRON_SECRET.
CRON_DISPATCH_PATH = "/__scheduled"


class CronEvent:
    """Stand-in for the ScheduledController the runtime would pass."""

    type = "scheduled"

    def __init__(self, cron, scheduled_time):
        self.cron = cron
        self.scheduledTime = scheduled_time


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(request.url)
        path = url.path

        if path == CRON_DISPATCH_PATH:
            return await self.handle_cron_dispatch(request)

        if path == "/api/health":
            return Response.json(
                {
                    "service": "blt-monitor",
                    "status": "ok",
                    "runtime": "cloudflare-python-workers",
                }
            )

        if path == "/api/run" and request.method == "POST":
            if not self.is_authorized(request):
                return Response.json({"error": "Unauthorized"}, status=401)

            try:
                shard = int(parse_qs(url.query).get("shard", ["0"])[0])
            except ValueError:
                return Response.json({"error": "Invalid shard"}, status=400)
            if shard not in range(HISTORY_SHARDS):
                return Response.json({"error": "Invalid shard"}, status=400)

            results = await self.run_monitors(shard)
            return Response.json({"results": results, "shard": shard, "shards": HISTORY_SHARDS})

        if path in ("/api/test-alert", "/api/test-slack") and request.method == "POST":
            if not self.is_authorized(request):
                return Response.json({"error": "Unauthorized"}, status=401)
            if not self.alert_webhook_url():
                return Response.json({"error": "Alert webhook is not configured"}, status=400)
            if not await self.send_alert("BLT Monitor: test alert. Alerts reach this channel."):
                return Response.json({"error": "Alert webhook rejected the message"}, status=502)

            return Response.json({"sent": True})

        if path == "/api/histories" and request.method == "GET":
            return Response.json(await self.load_all_histories())

        if path.startswith("/api/history/"):
            monitor_id = path.removeprefix("/api/history/")
            if not MONITOR_ID_PATTERN.fullmatch(monitor_id):
                return Response.json({"error": "Invalid monitor ID"}, status=400)

            if request.method == "GET":
                return await self.get_history(monitor_id)

            if request.method == "POST":
                return await self.append_history(request, monitor_id)

            return Response.json({"error": "Method not allowed"}, status=405)

        if path.startswith("/api/"):
            return Response.json({"error": "Not found"}, status=404)

        return await self.env.ASSETS.fetch(request)

    async def handle_cron_dispatch(self, request):
        if request.method != "POST":
            return Response.json({"ok": False, "error": "Method not allowed"}, status=405)
        expected = str(getattr(self.env, "CRON_SECRET", None) or "")
        provided = str(request.headers.get("X-BLT-Cron-Secret") or "")
        if not expected or not hmac.compare_digest(provided.encode(), expected.encode()):
            return Response.json({"ok": False, "error": "Forbidden"}, status=403)
        try:
            body = json.loads(await request.text() or "{}")
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        try:
            scheduled_time = int(body.get("scheduledTime"))
        except (TypeError, ValueError):
            scheduled_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        event = CronEvent(str(body.get("cron") or ""), scheduled_time)
        try:
            await self.scheduled(event, self.env, getattr(self, "ctx", None))
        except Exception as error:
            print(f"Dispatched scheduled run failed: {error}")
            return Response.json({"ok": False, "error": str(error)}, status=500)
        return Response.json({"ok": True})

    async def scheduled(self, controller, env, ctx):
        shard = int(controller.scheduledTime // SHARD_INTERVAL_MS) % HISTORY_SHARDS
        await self.run_monitors(shard, env)

    async def run_monitors(self, shard, env=None):
        env = env or self.env
        monitors = await self.load_monitors(env)
        histories = await self.load_histories(shard, env)
        if not histories:
            histories = await self.load_legacy_histories(monitors, shard, env)
        results = []

        for monitor in monitors:
            monitor_id = str(monitor.get("id", ""))
            if not monitor.get("enabled", True):
                print(f"Skipping disabled monitor: {monitor_id}")
                continue
            if not MONITOR_ID_PATTERN.fullmatch(monitor_id):
                print(f"Skipping monitor with invalid ID: {monitor_id}")
                continue
            if self.monitor_shard(monitor_id) != shard:
                continue

            previous = (histories.get(monitor_id) or [{}])[-1].get("status", "")
            result = await self.check_monitor(monitor)
            self.add_history_entry(histories, monitor_id, result)
            results.append({"id": monitor_id, "previous_status": previous, **result})

        await self.save_histories(shard, histories, env)
        await self.notify_changes(monitors, results, env)
        return [{key: value for key, value in result.items() if key != "previous_status"}
                for result in results]

    async def load_monitors(self, env=None):
        env = env or self.env
        response = await env.ASSETS.fetch("https://assets.local/monitors.json")
        if not response.ok:
            raise RuntimeError("Unable to load monitors.json")
        return json.loads(await response.text())

    async def check_monitor(self, monitor):
        started_at = perf_counter()
        keyword_status = "not_found"
        status = "failure"

        try:
            response = await fetch(str(monitor["url"]))
            content = await response.text()
            keyword = str(monitor.get("keyword", "")).lower()
            keyword_status = "found" if keyword in content.lower() else "not_found"
            cloudflare_captcha = (
                "verify you are human by completing the action below" in content.lower()
            )
            if response.ok and (keyword_status == "found" or cloudflare_captcha):
                status = "success"
        except Exception as error:
            print(f"Monitor request failed for {monitor.get('id')}: {error}")

        return {
            "datetime": datetime.now(timezone.utc).isoformat(),
            "duration_ms": round((perf_counter() - started_at) * 1000),
            "status": status,
            "keyword_status": keyword_status,
        }

    async def get_history(self, monitor_id):
        history = await self.load_history(monitor_id)
        return Response.json(history)

    async def append_history(self, request, monitor_id):
        if not self.is_authorized(request):
            return Response.json({"error": "Unauthorized"}, status=401)

        try:
            entry = json.loads(await request.text())
            entry = {
                "datetime": str(entry["datetime"]),
                "duration_ms": int(entry["duration_ms"]),
                "status": str(entry["status"]),
                "keyword_status": str(entry["keyword_status"]),
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return Response.json({"error": "Invalid history entry"}, status=400)

        if entry["duration_ms"] < 0:
            return Response.json({"error": "Invalid duration"}, status=400)
        if entry["status"] not in {"success", "failure"}:
            return Response.json({"error": "Invalid status"}, status=400)
        if entry["keyword_status"] not in {"found", "not_found"}:
            return Response.json({"error": "Invalid keyword status"}, status=400)

        history = await self.store_entry(monitor_id, entry)
        return Response.json({"stored": True, "entries": len(history)})

    async def store_entry(self, monitor_id, entry):
        shard = self.monitor_shard(monitor_id)
        histories = await self.load_histories(shard)
        history = self.add_history_entry(histories, monitor_id, entry)
        await self.save_histories(shard, histories)
        return history

    @staticmethod
    def alert_lines(monitors, results):
        """Lines for monitors that went down or came back since their last check.

        A site that stays down is reported once, not on every run.
        """
        names = {monitor.get("id"): monitor for monitor in monitors}
        down, recovered = [], []
        for result in results:
            monitor = names.get(result["id"]) or {}
            label = f"{monitor.get('name', result['id'])} ({monitor.get('url', '')})"
            if result["status"] == "failure" and result.get("previous_status") != "failure":
                down.append(f"- DOWN: {label}")
            elif result["status"] == "success" and result.get("previous_status") == "failure":
                recovered.append(f"- Back up: {label}")
        return down + recovered

    def alert_webhook_url(self, env=None):
        env = env or self.env
        # ALERT_WEBHOOK_URL is a forge chat channel's incoming webhook; it takes
        # the same {"text": ...} body as a Slack incoming webhook, which still
        # works as SLACK_WEBHOOK_URL.
        return str(getattr(env, "ALERT_WEBHOOK_URL", "") or getattr(env, "SLACK_WEBHOOK_URL", "") or "")

    async def notify_changes(self, monitors, results, env=None):
        lines = self.alert_lines(monitors, results)
        if not lines or not self.alert_webhook_url(env):
            return
        await self.send_alert(
            "BLT Monitor\n" + "\n".join(lines) + "\nhttps://monitor.owaspblt.org/",
            env,
        )

    async def send_alert(self, message, env=None):
        webhook_url = self.alert_webhook_url(env)
        if not webhook_url:
            return False
        try:
            response = await fetch(
                webhook_url,
                method="POST",
                headers={"Content-Type": "application/json"},
                body=json.dumps({"text": message}),
            )
        except Exception as error:
            print(f"Alert delivery failed: {error}")
            return False
        if not response.ok:
            print(f"Alert webhook answered HTTP {response.status}")
        return bool(response.ok)

    async def load_history(self, monitor_id):
        histories = await self.load_histories(self.monitor_shard(monitor_id))
        return histories.get(monitor_id, [])

    async def load_all_histories(self):
        all_histories = {}
        for shard in range(HISTORY_SHARDS):
            all_histories.update(await self.load_histories(shard))
        return all_histories

    async def load_histories(self, shard, env=None):
        raw_history = await self.history_store(env).get(self.histories_key(shard))
        if not raw_history:
            return {}

        try:
            histories = json.loads(raw_history)
            return histories if isinstance(histories, dict) else {}
        except json.JSONDecodeError:
            return {}

    async def load_legacy_histories(self, monitors, shard, env=None):
        histories = {}
        for monitor in monitors:
            monitor_id = str(monitor.get("id", ""))
            if (
                not MONITOR_ID_PATTERN.fullmatch(monitor_id)
                or self.monitor_shard(monitor_id) != shard
            ):
                continue

            raw_history = await self.history_store(env).get(self.history_key(monitor_id))
            if not raw_history:
                continue

            try:
                history = json.loads(raw_history)
                if isinstance(history, list):
                    histories[monitor_id] = history[-MAX_HISTORY_ENTRIES:]
            except json.JSONDecodeError:
                continue
        return histories

    async def save_histories(self, shard, histories, env=None):
        await self.history_store(env).put(self.histories_key(shard), json.dumps(histories))

    @staticmethod
    def add_history_entry(histories, monitor_id, entry):
        history = histories.get(monitor_id, [])
        history.append(entry)
        history = history[-MAX_HISTORY_ENTRIES:]
        histories[monitor_id] = history
        return history

    @staticmethod
    def history_key(monitor_id):
        return f"history:{monitor_id}"

    @staticmethod
    def histories_key(shard):
        return f"histories:{shard}"

    @staticmethod
    def monitor_shard(monitor_id):
        return sum(
            (index + 1) * byte for index, byte in enumerate(monitor_id.encode("utf-8"))
        ) % HISTORY_SHARDS

    def history_store(self, env=None):
        env = env or self.env
        return getattr(env, HISTORY_BINDING)

    def is_authorized(self, request):
        expected_token = getattr(self.env, "INGEST_TOKEN", "")
        supplied_token = request.headers.get("Authorization") or ""
        return bool(expected_token) and hmac.compare_digest(
            supplied_token.encode(), f"Bearer {expected_token}".encode()
        )
