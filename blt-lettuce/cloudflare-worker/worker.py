"""
Cloudflare Python Worker for BLT-Lettuce Slack Bot.

This worker handles webhook events, sends welcome messages,
tracks stats, serves the homepage, and handles all Slack interactions.
Designed to be deployed to any Slack organization.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone

from js import Response, fetch

# Channel IDs - these can be configured via environment variables
# NOTE: These are OWASP-specific defaults. For other organizations:
# - Either set these via environment variables (see wrangler.toml)
# - Or leave as None to disable channel-specific features
DEFAULT_DEPLOYS_CHANNEL = None  # Optional: "#project-blt-lettuce-deploys"
DEFAULT_JOINS_CHANNEL_ID = None  # Optional: Channel for join notifications
DEFAULT_CONTRIBUTE_ID = None  # Optional: Channel for contribution guidelines

# Stats are stored in Cloudflare KV namespace
# Stats structure: { "joins": int, "commands": int, "last_updated": str }


def get_utc_now():
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


# Welcome message template
WELCOME_MESSAGE = (
    ":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
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
            return stats
    except Exception:
        pass
    # If not found, return default stats
    return {"joins": 0, "commands": 0, "last_updated": get_utc_now()}


async def save_stats(env, stats):
    """Save stats to KV store."""
    stats["last_updated"] = get_utc_now()
    await env.STATS_KV.put("stats", json.dumps(stats))


async def increment_joins(env):
    """Increment the joins counter."""
    stats = await get_stats(env)
    stats["joins"] = stats.get("joins", 0) + 1
    await save_stats(env, stats)
    return stats


async def increment_commands(env):
    """Increment the commands counter."""
    stats = await get_stats(env)
    stats["commands"] = stats.get("commands", 0) + 1
    await save_stats(env, stats)
    return stats


async def get_bot_user_id(env):
    """Get the bot's user ID from Slack API."""
    slack_token = getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return None

    try:
        response = await fetch(
            "https://slack.com/api/auth.test",
            {
                "method": "POST",
                "headers": {
                    "Authorization": f"Bearer {slack_token}",
                },
            },
        )
        result = await response.json()
        if result.get("ok"):
            return result.get("user_id")
    except Exception:
        pass
    return None


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

    # Get channel IDs from env or use defaults
    joins_channel = getattr(env, "JOINS_CHANNEL_ID", DEFAULT_JOINS_CHANNEL_ID)

    # Post a message in the private joins channel (if configured)
    if joins_channel:
        try:
            await send_slack_message(env, joins_channel, f"<@{user_id}> joined the team.")
        except Exception:
            pass  # Don't fail if we can't post to joins channel

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


async def handle_message_event(env, event):
    """Handle a message event - detect keywords and respond."""
    message_text = event.get("text", "").lower()
    user = event.get("user")
    channel = event.get("channel")
    channel_type = event.get("channel_type")
    subtype = event.get("subtype")

    # Get bot user ID to avoid responding to self
    bot_user_id = await get_bot_user_id(env)

    # Don't respond to bot's own messages
    if user == bot_user_id:
        return {"ok": True, "message": "Ignoring bot message"}

    # Get channel IDs from env or use defaults
    contribute_id = getattr(env, "CONTRIBUTE_ID", DEFAULT_CONTRIBUTE_ID)
    joins_channel = getattr(env, "JOINS_CHANNEL_ID", DEFAULT_JOINS_CHANNEL_ID)

    # Handle "contribute" keyword detection (but not #contribute)
    if (
        subtype is None
        and "#contribute" not in message_text
        and any(
            keyword in message_text for keyword in ("contribute", "contributing", "contributes")
        )
    ):
        response_text = (
            f"Hello <@{user}>! Please check this channel "
            f"<#{contribute_id}> for contributing guidelines today!"
        )
        result = await send_slack_message(env, channel, response_text)
        return {"ok": result.get("ok"), "action": "contribute_response"}

    # Handle direct messages
    if channel_type == "im":
        # Log to joins channel (if configured)
        if joins_channel:
            try:
                await send_slack_message(env, joins_channel, f"<@{user}> said {message_text}")
            except Exception:
                pass

        # Respond to the user
        response_text = f"Hello <@{user}>, you said: {event.get('text', '')}"
        result = await send_slack_message(env, user, response_text)
        return {"ok": result.get("ok"), "action": "dm_response"}

    return {"ok": True, "message": "No action taken"}


async def handle_command(env, event):
    """Handle a command event."""
    # Increment commands counter
    await increment_commands(env)
    return {"ok": True, "message": "Command tracked"}


def verify_slack_signature(signing_secret, timestamp, body, signature):
    """Verify that the request came from Slack using the signing secret."""
    if not signing_secret or not timestamp or not signature:
        return False

    # Check timestamp to prevent replay attacks (allow 5 minutes)
    try:
        request_time = int(timestamp)
        current_time = int(datetime.now(timezone.utc).timestamp())
        if abs(current_time - request_time) > 300:
            return False
    except (ValueError, TypeError):
        return False

    # Calculate expected signature
    sig_basestring = f"v0:{timestamp}:{body}"
    expected_signature = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    # Compare signatures using constant-time comparison
    return hmac.compare_digest(expected_signature, signature)


def is_homepage_request(url, method):
    """Check if the request is for the homepage."""
    if method != "GET":
        return False

    # Check if it's a root path or index request
    path = url.split("?")[0]  # Remove query parameters
    path_segments = path.split("/")
    last_segment = path_segments[-1] if path_segments else ""

    # Match root path, index, or paths without file extensions
    return (
        path.endswith("/")
        or "/index" in path
        or last_segment == ""
        or ("." not in last_segment and last_segment not in ["webhook", "stats", "health"])
    )


def get_homepage_html():
    # This is a simple placeholder - in production, you'd load from a file or KV
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BLT-Lettuce | OWASP Slack Bot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
</head>
<body class="bg-gray-50 font-sans text-gray-900">
    <nav class="bg-white shadow-lg sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center">
                    <h1 class="text-xl font-bold text-gray-900">🥬 BLT-Lettuce</h1>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="https://github.com/OWASP-BLT/BLT-Lettuce" target="_blank"
                       class="text-gray-500 hover:text-gray-900">
                        <i class="fab fa-github text-xl"></i> Contribute
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <section class="bg-white rounded-lg shadow p-8 mb-8 text-center">
            <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
                BLT-Lettuce <span class="text-red-600">Slack Bot</span>
            </h1>
            <p class="text-xl text-gray-700 mb-8">
                An intelligent OWASP Slack bot that welcomes new community members,
                helps them discover security projects, and connects the global
                cybersecurity community.
            </p>
            <div class="flex justify-center gap-4 flex-wrap">
                <a href="https://owasp.org/slack/invite"
                   class="inline-flex items-center px-6 py-3 bg-red-600 text-white rounded-lg
                          hover:bg-red-700 transition-colors font-semibold shadow-md"
                   target="_blank">
                    <i class="fab fa-slack mr-2"></i> Join OWASP Slack
                </a>
                <a href="https://github.com/OWASP-BLT/BLT-Lettuce"
                   class="inline-flex items-center px-6 py-3 bg-white border border-gray-300
                          text-gray-700 rounded-lg hover:bg-gray-50 transition-colors
                          font-semibold shadow-sm"
                   target="_blank">
                    <i class="fab fa-github mr-2"></i> Star on GitHub
                </a>
            </div>
        </section>

        <section class="bg-white rounded-lg shadow p-6 mb-8" id="stats">
            <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">Live Community Stats</h2>
            <div id="stats-container" class="grid md:grid-cols-3 gap-6">
                <div class="col-span-3 text-center py-10 text-gray-500">
                    <i class="fas fa-circle-notch fa-spin text-3xl text-red-600 mb-2"></i>
                    <p>Loading live statistics...</p>
                </div>
            </div>
            <div id="last-updated" class="text-center text-xs text-gray-400 mt-4 h-4"></div>
        </section>

        <section class="bg-white rounded-lg shadow p-6 mb-8">
            <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">
                What BLT-Lettuce Does
            </h2>
            <div class="grid md:grid-cols-3 gap-8">
                <div class="text-center p-4 hover:bg-gray-50 rounded-xl transition-colors">
                    <div class="w-16 h-16 bg-red-100 text-red-600 rounded-2xl flex items-center
                                justify-center mx-auto mb-4 text-2xl">👋</div>
                    <h3 class="text-xl font-bold text-gray-900 mb-2">Smart Welcome System</h3>
                    <p class="text-gray-600">Automatically welcomes new Slack members with
                       personalized messages and project recommendations.</p>
                </div>
                <div class="text-center p-4 hover:bg-gray-50 rounded-xl transition-colors">
                    <div class="w-16 h-16 bg-red-100 text-red-600 rounded-2xl flex items-center
                                justify-center mx-auto mb-4 text-2xl">🔍</div>
                    <h3 class="text-xl font-bold text-gray-900 mb-2">Project Discovery</h3>
                    <p class="text-gray-600">Helps members find OWASP projects matching their
                       skills and interests.</p>
                </div>
                <div class="text-center p-4 hover:bg-gray-50 rounded-xl transition-colors">
                    <div class="w-16 h-16 bg-red-100 text-red-600 rounded-2xl flex items-center
                                justify-center mx-auto mb-4 text-2xl">🐙</div>
                    <h3 class="text-xl font-bold text-gray-900 mb-2">GitHub Integration</h3>
                    <p class="text-gray-600">Fetches real-time data from OWASP repositories.</p>
                </div>
            </div>
        </section>

        <section class="mb-12 text-center">
            <h2 class="text-2xl font-bold text-gray-900 mb-6">Built With</h2>
            <div class="flex flex-wrap justify-center gap-3">
                <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium
                             border border-gray-200">🐍 Python</span>
                <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium
                             border border-gray-200">☁️ Cloudflare Workers</span>
                <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium
                             border border-gray-200">💬 Slack API</span>
                <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium
                             border border-gray-200">🗄️ KV Storage</span>
            </div>
        </section>

        <footer class="bg-white border-t py-8 mt-12">
            <div class="max-w-7xl mx-auto px-4 text-center">
                <p class="text-gray-600 mb-4">
                    Made with ❤️ by the
                    <a href="https://owasp.org/www-project-bug-logging-tool/" target="_blank"
                       class="text-red-600 hover:underline font-medium">OWASP BLT Team</a>
                </p>
                <div class="flex justify-center space-x-6 text-sm text-gray-500">
                    <a href="https://github.com/OWASP-BLT/BLT-Lettuce"
                       class="hover:text-red-600 transition-colors">GitHub</a>
                    <a href="https://owasp.org/slack/invite"
                       class="hover:text-red-600 transition-colors">Join Slack</a>
                    <a href="https://owasp.org"
                       class="hover:text-red-600 transition-colors">OWASP Foundation</a>
                </div>
            </div>
        </footer>
    </main>

    <script>
        const STATS_API_URL = window.location.origin + "/stats";

        const formatNumber = (num) => {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
            if (num >= 1000) return (num / 1000).toFixed(1) + "K";
            return num.toLocaleString();
        };

        async function fetchStats() {
            try {
                const response = await fetch(STATS_API_URL);
                if (!response.ok) throw new Error("Failed to fetch stats");
                return await response.json();
            } catch (error) {
                console.error("Stats fetch error:", error);
                return { joins: 0, commands: 0, last_updated: new Date().toISOString() };
            }
        }

        function renderStats(stats) {
            const container = document.getElementById("stats-container");
            const teamJoins = stats.team_joins || stats.joins || 0;
            const commands = stats.commands || 0;
            const totalActivities = stats.total_activities || teamJoins + commands;

            container.innerHTML = `
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center
                                justify-center mx-auto mb-3 text-xl">
                        <i class="fas fa-user-plus"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900">${formatNumber(teamJoins)}</h3>
                    <p class="text-gray-600 text-sm">Members Welcomed</p>
                </div>
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center
                                justify-center mx-auto mb-3 text-xl">
                        <i class="fas fa-terminal"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900">${formatNumber(commands)}</h3>
                    <p class="text-gray-600 text-sm">Commands Processed</p>
                </div>
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center
                                justify-center mx-auto mb-3 text-xl">
                        <i class="fas fa-chart-line"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900">
                        ${formatNumber(totalActivities)}
                    </h3>
                    <p class="text-gray-600 text-sm">Total Activities</p>
                </div>
            `;

            if (stats.last_updated) {
                const date = new Date(stats.last_updated).toLocaleDateString();
                document.getElementById("last-updated").textContent = `Last updated: ${date}`;
            }
        }

        async function init() {
            const stats = await fetchStats();
            renderStats(stats);
        }

        init();
    </script>
</body>
</html>"""


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

    # Homepage - serve HTML
    if is_homepage_request(url, method):
        html_content = get_homepage_html()
        return Response.new(
            html_content,
            {
                "headers": {
                    "Content-Type": "text/html",
                    "Cache-Control": "public, max-age=300",
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
            # Get raw body for signature verification
            body_text = await request.text()

            # Verify Slack signature (skip for url_verification)
            body_json = json.loads(body_text)
            if body_json.get("type") != "url_verification":
                signing_secret = getattr(env, "SIGNING_SECRET", None)
                timestamp = request.headers.get("X-Slack-Request-Timestamp")
                signature = request.headers.get("X-Slack-Signature")

                if not verify_slack_signature(signing_secret, timestamp, body_text, signature):
                    return Response.json({"error": "Invalid signature"}, {"status": 401})

            # Handle Slack URL verification challenge
            if body_json.get("type") == "url_verification":
                return Response.json({"challenge": body_json.get("challenge")})

            # Handle events
            event = body_json.get("event", {})
            event_type = event.get("type")

            if event_type == "team_join":
                result = await handle_team_join(env, event)
                return Response.json(result)

            if event_type == "message":
                result = await handle_message_event(env, event)
                return Response.json(result)

            if event_type == "app_mention" or body_json.get("command"):
                result = await handle_command(env, event)
                return Response.json(result)

            return Response.json({"ok": True, "message": "Event received"})

        except Exception:
            # Return sanitized error message to avoid exposing internal details
            return Response.json({"error": "Internal server error"}, {"status": 500})

    # Health check endpoint
    if "/health" in url:
        return Response.json({"status": "ok", "timestamp": get_utc_now()})

    # Default response - API information
    return Response.json(
        {
            "message": "BLT-Lettuce Cloudflare Worker",
            "version": "2.0",
            "endpoints": {
                "/": "GET - Homepage",
                "/webhook": "POST - Slack webhook endpoint",
                "/stats": "GET - Get current stats",
                "/health": "GET - Health check",
            },
        }
    )
