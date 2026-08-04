"""
Cloudflare Durable Object for handling AI conversations.
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from js import Date, Headers, Response, URL

logger = logging.getLogger("toasty.conversation_do")

MAX_ACTIVE_TURNS = 5
TTL_30_DAYS_MS = 30 * 24 * 60 * 60 * 1000
TTL_CLEANUP_MS = 60 * 60 * 1000  # 1 hour
VALID_ROLES = {"developer", "ai"}


def _json_response(data: dict[str, Any], status: int = 200) -> Response:
    headers = Headers.new()
    headers.set("Content-Type", "application/json")
    return Response.new(json.dumps(data), headers=headers, status=status)


class ConversationDO:
    """Core ConversationDO class implementing a 5-turn rolling context buffer."""

    def __init__(self, state: Any, env: Any) -> None:
        self.state = state
        self.storage = state.storage
        self.env = env

    async def fetch(self, request: Any) -> Response:
        try:
            url = URL.new(request.url)
            pathname = url.pathname

            if request.method == "POST" and pathname == "/reply":
                return await self._handle_reply(request)
            elif request.method == "GET" and pathname == "/history":
                return await self._handle_history(url)
            elif request.method == "DELETE" and pathname == "/archive":
                return await self._handle_archive()
            else:
                return _json_response({"error": "Not Found"}, status=404)
        except Exception as e:
            logger.exception("Error processing request: %s", e)
            return _json_response({"error": "Internal Server Error"}, status=500)

    async def _handle_reply(self, request: Any) -> Response:
        text = await request.text()
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            return _json_response({"error": "Invalid JSON body"}, status=400)

        role = body.get("role")
        content = body.get("content")
        triage_id = body.get("triage_id")

        if role not in VALID_ROLES:
            return _json_response({"error": f"Invalid role, must be one of {VALID_ROLES}"}, status=400)
        if not content or not isinstance(content, str):
            return _json_response({"error": "Content must be a non-empty string"}, status=400)
        if len(content) > 20000:
            return _json_response({"error": "Content exceeds maximum allowed length of 20000 characters"}, status=400)
        if not triage_id:
            return _json_response({"error": "triage_id is required"}, status=400)

        status = await self.storage.get("status")
        if status == "closed":
            return _json_response({"error": "Conversation is closed"}, status=409)

        turns_str = await self.storage.get("turns")
        turns: list[dict[str, Any]] = json.loads(turns_str) if turns_str else []
        turn_count = await self.storage.get("turn_count") or 0

        # Increment turn count
        turn_count += 1
        iso_now = datetime.now(timezone.utc).isoformat()
        if not iso_now.endswith("Z"):
            iso_now = iso_now.replace("+00:00", "Z")
        new_turn = {"role": role, "content": content, "timestamp": iso_now, "turn_index": turn_count}
        turns.append(new_turn)

        while len(turns) > MAX_ACTIVE_TURNS:
            oldest_turn = turns[0]
            try:
                # Archive to D1
                sql = (
                    "INSERT INTO conversation_archive "
                    "(id, triage_event_id, role, content, turn_index) "
                    "VALUES (?, ?, ?, ?, ?)"
                )
                id_hex = secrets.token_hex(16)
                await self.env.DB.prepare(sql).bind(
                    id_hex,
                    triage_id,  # Use triage_id passed in the request
                    oldest_turn["role"],
                    oldest_turn["content"],
                    oldest_turn["turn_index"],
                ).run()
                # Remove oldest only after confirmed write
                turns.pop(0)
            except Exception as e:
                logger.warning("Failed to archive turn to D1, keeping in DO: %s", e)
                break

        # Save state
        await self.storage.put("turns", json.dumps(turns))
        await self.storage.put("turn_count", turn_count)

        if turn_count == 1:
            await self.storage.put("conversation_id", triage_id)
            await self.storage.put("status", "active")

        # Set alarm for 30 days
        await self.storage.setAlarm(Date.now() + TTL_30_DAYS_MS)

        return _json_response({"turn_count": turn_count, "conversation_id": triage_id})

    async def _handle_history(self, url: Any) -> Response:
        status = await self.storage.get("status")
        conversation_id = await self.storage.get("conversation_id")
        turn_count = await self.storage.get("turn_count") or 0
        turns_str = await self.storage.get("turns")
        turns = json.loads(turns_str) if turns_str else []

        full_history = url.searchParams.get("full") == "true"
        if full_history and conversation_id:
            try:
                turn_cursor = int(url.searchParams.get("cursor") or 0)
                sql = (
                    "SELECT role, content, created_at as timestamp, turn_index "
                    "FROM conversation_archive "
                    "WHERE triage_event_id = ? AND turn_index > ? "
                    "ORDER BY turn_index ASC LIMIT 50"
                )
                result = await self.env.DB.prepare(sql).bind(conversation_id, turn_cursor).all()
                archived_turns_raw = getattr(result, "results", []) or []

                formatted_archived = []
                for row in archived_turns_raw:
                    # Normalize SQL timestamp to ISO-8601
                    ts = row.timestamp
                    if ts and not ts.endswith("Z"):
                        ts = ts.replace(" ", "T") + "Z"
                    formatted_archived.append(
                        {
                            "role": row.role,
                            "content": row.content,
                            "timestamp": ts,
                            "turn_index": row.turn_index,
                        }
                    )

                all_turns = formatted_archived + turns
                all_turns.sort(key=lambda t: t.get("turn_index", 0))
                turns = all_turns
            except Exception as e:
                logger.warning("Failed to fetch archived history from D1: %s", e)

        return _json_response(
            {"conversation_id": conversation_id, "turns": turns, "turn_count": turn_count, "status": status}
        )

    async def _handle_archive(self) -> Response:
        turns_str = await self.storage.get("turns")
        turns = json.loads(turns_str) if turns_str else []
        conversation_id = await self.storage.get("conversation_id")

        archived_count = 0
        failed_turns = []
        if conversation_id and turns:
            for turn in turns:
                try:
                    sql = (
                        "INSERT INTO conversation_archive "
                        "(id, triage_event_id, role, content, turn_index) "
                        "VALUES (?, ?, ?, ?, ?)"
                    )
                    id_hex = secrets.token_hex(16)
                    await self.env.DB.prepare(sql).bind(
                        id_hex,
                        conversation_id,
                        turn["role"],
                        turn["content"],
                        turn["turn_index"],
                    ).run()
                    archived_count += 1
                except Exception as e:
                    logger.warning("Failed to archive turn during DELETE: %s", e)
                    failed_turns.append(turn)

        await self.storage.put("status", "closed")
        if failed_turns:
            await self.storage.put("turns", json.dumps(failed_turns))
            await self.storage.setAlarm(Date.now() + 60000)  # Retry in 1 minute
            return _json_response(
                {"archived": False, "turns_archived": archived_count, "failed_count": len(failed_turns)}
            )

        await self.storage.deleteAll()
        return _json_response({"archived": True, "turns_archived": archived_count})

    async def alarm(self) -> None:
        status = await self.storage.get("status")
        turns_str = await self.storage.get("turns")
        turns = json.loads(turns_str) if turns_str else []

        if status == "active":
            await self.storage.setAlarm(Date.now() + TTL_30_DAYS_MS)
        elif turns:
            await self._handle_archive()
        else:
            await self.storage.deleteAll()
