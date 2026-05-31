import json
import re
from datetime import datetime, timezone
from time import perf_counter
from urllib.parse import parse_qs, urlparse

from workers import Response, WorkerEntrypoint, fetch

MAX_HISTORY_ENTRIES = 30
HISTORY_BINDING = "blt-monitor-history"
HISTORY_SHARDS = 4
SCHEDULE_SHARDS = {
    "*/10 * * * *": 0,
    "1-59/10 * * * *": 1,
    "2-59/10 * * * *": 2,
    "3-59/10 * * * *": 3,
}
MONITOR_ID_PATTERN = re.compile(r"^[a-z0-9_-]+$")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(request.url)
        path = url.path

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

        if path == "/api/test-slack" and request.method == "POST":
            if not self.is_authorized(request):
                return Response.json({"error": "Unauthorized"}, status=401)
            if not await self.send_slack("Slack webhook test successful."):
                return Response.json({"error": "Slack webhook is not configured"}, status=400)

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

    async def scheduled(self, controller, env, ctx):
        await self.run_monitors(SCHEDULE_SHARDS[controller.cron])

    async def run_monitors(self, shard):
        monitors = await self.load_monitors()
        histories = await self.load_histories(shard)
        if not histories:
            histories = await self.load_legacy_histories(monitors, shard)
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

            result = await self.check_monitor(monitor)
            self.add_history_entry(histories, monitor_id, result)
            results.append({"id": monitor_id, **result})

        await self.save_histories(shard, histories)
        await self.notify_failures(monitors, results)
        return results

    async def load_monitors(self):
        response = await self.env.ASSETS.fetch("https://assets.local/monitors.json")
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

    async def notify_failures(self, monitors, results):
        webhook_url = getattr(self.env, "SLACK_WEBHOOK_URL", "")
        failed_ids = {result["id"] for result in results if result["status"] == "failure"}
        if not webhook_url or not failed_ids:
            return

        failed_monitors = [
            f"- {monitor['name']} ({monitor['url']})"
            for monitor in monitors
            if monitor.get("id") in failed_ids
        ]
        await self.send_slack(
            "Website Monitor Alert\n"
            "One or more monitors detected issues:\n"
            + "\n".join(failed_monitors)
        )

    async def send_slack(self, message):
        webhook_url = getattr(self.env, "SLACK_WEBHOOK_URL", "")
        if not webhook_url:
            return False

        await fetch(
            webhook_url,
            method="POST",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"text": message}),
        )
        return True

    async def load_history(self, monitor_id):
        histories = await self.load_histories(self.monitor_shard(monitor_id))
        return histories.get(monitor_id, [])

    async def load_all_histories(self):
        all_histories = {}
        for shard in range(HISTORY_SHARDS):
            all_histories.update(await self.load_histories(shard))
        return all_histories

    async def load_histories(self, shard):
        raw_history = await self.history_store.get(self.histories_key(shard))
        if not raw_history:
            return {}

        try:
            histories = json.loads(raw_history)
            return histories if isinstance(histories, dict) else {}
        except json.JSONDecodeError:
            return {}

    async def load_legacy_histories(self, monitors, shard):
        histories = {}
        for monitor in monitors:
            monitor_id = str(monitor.get("id", ""))
            if (
                not MONITOR_ID_PATTERN.fullmatch(monitor_id)
                or self.monitor_shard(monitor_id) != shard
            ):
                continue

            raw_history = await self.history_store.get(self.history_key(monitor_id))
            if not raw_history:
                continue

            try:
                history = json.loads(raw_history)
                if isinstance(history, list):
                    histories[monitor_id] = history[-MAX_HISTORY_ENTRIES:]
            except json.JSONDecodeError:
                continue
        return histories

    async def save_histories(self, shard, histories):
        await self.history_store.put(self.histories_key(shard), json.dumps(histories))

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

    @property
    def history_store(self):
        return getattr(self.env, HISTORY_BINDING)

    def is_authorized(self, request):
        expected_token = getattr(self.env, "INGEST_TOKEN", "")
        supplied_token = request.headers.get("Authorization") or ""
        return bool(expected_token) and supplied_token == f"Bearer {expected_token}"
