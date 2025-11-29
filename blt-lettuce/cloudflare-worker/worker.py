"""
Cloudflare Python Worker for BLT-Lettuce Slack Bot.

This worker handles webhook events, sends welcome messages,
and tracks stats for joins and commands.
"""

import json
from datetime import datetime, timezone

from js import Response, fetch

# Stats are stored in Cloudflare KV namespace
# Stats structure: { "joins": int, "commands": int, "last_updated": str }


def get_utc_now():
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


WELCOME_MESSAGE = (
    ":tada: *Welcome to the OWASP Slack Community, {user_id}!* :tada:\n\n"
    "We're thrilled to have you here! Whether you're new to OWASP or a "
    "long-time contributor, this Slack workspace is the perfect place to "
    "connect, collaborate, and stay informed about all things OWASP.\n\n"
    ":small_blue_diamond: *Get Involved:*\n"
    "• Check out the *#contribute* channel to find ways to get involved "
    "with OWASP projects and initiatives.\n"
    "• Explore individual project channels, which are named *#project-name*, "
    "to dive into specific projects that interest you.\n"
    "• Join our chapter channels, named *#chapter-name*, to connect with "
    "local OWASP members in your area.\n\n"
    ":small_blue_diamond: *Stay Updated:*\n"
    "• Visit *#newsroom* for the latest updates and announcements.\n"
    "• Follow *#external-activities* for news about OWASP's engagement "
    "with the wider security community.\n\n"
    ":small_blue_diamond: *Connect and Learn:*\n"
    "• *#jobs*: Looking for new opportunities? Check out the latest "
    "job postings here.\n"
    "• *#leaders*: Connect with OWASP leaders and stay informed about "
    "leadership activities.\n"
    "• *#project-committee*: Engage with the committee overseeing "
    "OWASP projects.\n"
    "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
    "• *#github-admins*: Get support and discuss issues related to "
    "OWASP's GitHub repositories.\n"
    "• *#learning*: Share and find resources to expand your knowledge "
    "in the field of application security.\n\n"
    "We're excited to see the amazing contributions you'll make. If you "
    "have any questions or need assistance, don't hesitate to ask. Let's "
    "work together to make software security visible and improve the "
    "security of the software we all rely on.\n\n"
    "Welcome aboard! :rocket:"
)


async def get_stats(env):
    """Get current stats and version from KV store."""
    try:
        # Use getWithMetadata to get the value and its metadata (including version/etag)
        result = await env.STATS_KV.getWithMetadata("stats", "json")
        if result and result.value is not None:
            stats = result.value
            version = getattr(result, "metadata", {}).get("version", None)
            etag = getattr(result, "etag", None)
            return stats, etag
    except Exception:
        pass
    # If not found, return default stats and None for etag
    return {"joins": 0, "commands": 0, "last_updated": get_utc_now()}, None


async def save_stats(env, stats, etag=None):
    """Save stats to KV store with optional optimistic locking."""
    stats["last_updated"] = get_utc_now()
    options = {}
    if etag:
        options["if_match"] = etag
    await env.STATS_KV.put("stats", json.dumps(stats), **options)


async def increment_joins(env, max_retries=5):
    """Increment the joins counter atomically with optimistic locking."""
    for _ in range(max_retries):
        stats, etag = await get_stats(env)
        stats["joins"] = stats.get("joins", 0) + 1
        try:
            await save_stats(env, stats, etag)
            return stats
        except Exception as e:
            # If the put failed due to version conflict, retry
            continue
    raise Exception("Failed to increment joins after multiple retries due to concurrent updates.")


async def increment_commands(env, max_retries=5):
    """Increment the commands counter atomically with optimistic locking."""
    for _ in range(max_retries):
        stats, etag = await get_stats(env)
        stats["commands"] = stats.get("commands", 0) + 1
        try:
            await save_stats(env, stats, etag)
            return stats
        except Exception as e:
            # If the put failed due to version conflict, retry
            continue
    raise Exception("Failed to increment commands after multiple retries due to concurrent updates.")


async def send_slack_message(env, channel, text, blocks=None):
    """Send a message to Slack."""
    slack_token = getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return {"ok": False, "error": "SLACK_TOKEN not configured"}

    payload = {
        "channel": channel,
        "text": text,
    }
    if blocks:
        payload["blocks"] = blocks

    response = await fetch(
        "https://slack.com/api/chat.postMessage",
        {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {slack_token}",
            },
            "body": json.dumps(payload),
        },
    )
    return await response.json()


async def open_conversation(env, user_id):
    """Open a DM conversation with a user."""
    slack_token = getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return {"ok": False, "error": "SLACK_TOKEN not configured"}

    response = await fetch(
        "https://slack.com/api/conversations.open",
        {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {slack_token}",
            },
            "body": json.dumps({"users": user_id}),
        },
    )
    return await response.json()


async def handle_team_join(env, event):
    """Handle a team_join event - send welcome message to new user."""
    user_id = event.get("user", {}).get("id")
    if not user_id:
        return {"error": "No user ID in event"}

    # Increment joins counter
    await increment_joins(env)

    # Open DM with user
    dm_response = await open_conversation(env, user_id)
    if not dm_response.get("ok"):
        return {"error": f"Failed to open DM: {dm_response.get('error')}"}

    dm_channel = dm_response.get("channel", {}).get("id")
    if not dm_channel:
        return {"error": "Failed to get DM channel ID"}

    # Format welcome message
    welcome_text = WELCOME_MESSAGE.format(user_id=user_id)
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": welcome_text.strip()}}]

    # Send welcome message
    result = await send_slack_message(
        env,
        dm_channel,
        "Welcome to the OWASP Slack Community!",
        blocks,
    )

    return {"ok": result.get("ok"), "user_id": user_id}


async def handle_command(env, event):
    """Handle a command event."""
    # Increment commands counter
    await increment_commands(env)
    return {"ok": True, "message": "Command tracked"}


async def on_fetch(request, env):
    """Main entry point for the Cloudflare Worker."""
    url = request.url
    method = request.method

    # Handle CORS preflight
    if method == "OPTIONS":
        return Response.new(
            "",
            {
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            },
        )

    # Stats endpoint - returns current stats as JSON
    if "/stats" in url and method == "GET":
        stats = await get_stats(env)
        return Response.json(
            stats,
            {
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
                },
            },
        )

    # Webhook endpoint for Slack events
    if "/webhook" in url and method == "POST":
        try:
            body = await request.json()

            # Handle Slack URL verification challenge
            if body.get("type") == "url_verification":
                return Response.json({"challenge": body.get("challenge")})

            # Handle events
            event = body.get("event", {})
            event_type = event.get("type")

            if event_type == "team_join":
                result = await handle_team_join(env, event)
                return Response.json(result)

            if event_type == "app_mention" or body.get("command"):
                result = await handle_command(env, event)
                return Response.json(result)

            return Response.json({"ok": True, "message": "Event received"})

        except Exception as e:
            return Response.json({"error": str(e)}, {"status": 500})

    # Health check endpoint
    if "/health" in url:
        return Response.json({"status": "ok", "timestamp": get_utc_now()})

    # Default response
    return Response.json(
        {
            "message": "BLT-Lettuce Cloudflare Worker",
            "endpoints": {
                "/webhook": "POST - Slack webhook endpoint",
                "/stats": "GET - Get current stats",
                "/health": "GET - Health check",
            },
        }
    )
