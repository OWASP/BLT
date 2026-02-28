"""
BLT-Byte: AI assistant, orchestrator and security agent for OWASP BLT.

Routes:
  GET  /           → Landing page (served from public/index.html via Assets binding)
  POST /api/chat   → FAQ + onboarding chat
  POST /api/scan   → Security scan orchestrator
  POST /api/mcp    → MCP (Model Context Protocol) server endpoint
  GET  /api/health → Health check
"""

import json
from pathlib import Path

from workers import Response, WorkerEntrypoint

# ---------------------------------------------------------------------------
# BLT FAQ knowledge base
# ---------------------------------------------------------------------------
FAQ_CONTEXT = """
You are Byte, the AI assistant for OWASP BLT (Bug Logging Tool).
OWASP BLT is a gamified, crowd-sourced QA testing and vulnerability disclosure
platform. Key facts:

- Website: https://www.bugheist.com / https://owasp.org/www-project-bug-logging-tool/
- GitHub: https://github.com/OWASP-BLT/BLT
- Purpose: Help security researchers discover, report, and get rewarded for
  finding bugs in websites, apps, and Git repositories.
- Key features: bug reporting, gamification (points, badges), leaderboards,
  organisation management, SIZZLE token rewards, Bacon (BLT's internal currency).
- Tech stack: Python/Django backend, Cloudflare Workers AI for Byte.
- Slack: https://owasp.org/slack/invite (channel #project-blt)

Onboarding steps for new contributors:
  1. Fork https://github.com/OWASP-BLT/BLT and clone locally.
  2. Copy .env.example to .env and fill in required credentials.
  3. Run `docker-compose up` (or follow the manual Django setup in CONTRIBUTING.md).
  4. Browse to http://localhost:8000.
  5. Pick a good-first-issue and submit a PR.

Onboarding steps for bug hunters:
  1. Register at https://www.bugheist.com.
  2. Choose a domain/project to test.
  3. Find a bug, screenshot it, submit a report.
  4. Earn points and climb the leaderboard.

Security scanning capabilities (via /api/scan):
  - Header analysis: checks for missing or misconfigured security headers.
  - SSL/TLS check: verifies certificate validity and protocol versions.
  - Open redirect detection hints.
  - Exposed sensitive files check.

MCP integration (/api/mcp):
  - Exposes BLT tool capabilities as MCP tools so AI IDEs (Cursor, Zed, etc.)
    can interact with BLT directly.
  - Available tools: search_bugs, submit_bug, get_leaderboard, scan_url.

Always be concise, friendly, and security-focused. If unsure, direct the user
to the BLT GitHub repository or Slack.
"""

SCAN_SYSTEM_PROMPT = """
You are a security analysis assistant for OWASP BLT. Given a URL or domain,
provide a structured security assessment covering:
1. Recommended security headers to check (CSP, HSTS, X-Frame-Options, etc.)
2. Common vulnerabilities to test for (OWASP Top 10 relevant items)
3. Suggested BLT report categories
4. Severity estimation guidance

Be precise, technical, and actionable. Format your response as JSON with keys:
"headers_to_check", "vulnerabilities_to_test", "blt_categories", "notes".
"""

# ---------------------------------------------------------------------------
# MCP tool manifest
# ---------------------------------------------------------------------------
MCP_MANIFEST = {
    "schema_version": "1.0",
    "name": "blt-byte",
    "description": "OWASP BLT AI assistant – FAQ, onboarding, and security scanning",
    "tools": [
        {
            "name": "chat",
            "description": "Ask Byte anything about OWASP BLT (FAQ, onboarding, how-tos)",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "User message"},
                    "history": {
                        "type": "array",
                        "description": "Prior conversation turns",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["message"],
            },
        },
        {
            "name": "scan_url",
            "description": "Generate a security scan checklist for a given URL or domain",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Target URL or domain"},
                    "scan_type": {
                        "type": "string",
                        "enum": ["quick", "full"],
                        "description": "Scan depth (default: quick)",
                    },
                },
                "required": ["url"],
            },
        },
        {
            "name": "get_onboarding_guide",
            "description": "Return the step-by-step onboarding guide for a given role",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "enum": ["contributor", "bug_hunter", "organisation"],
                        "description": "User role",
                    }
                },
                "required": ["role"],
            },
        },
    ],
}


# ---------------------------------------------------------------------------
# Helper: CORS headers
# ---------------------------------------------------------------------------
def cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def json_response(data: dict, status: int = 200) -> Response:
    return Response(
        json.dumps(data),
        status=status,
        headers={"Content-Type": "application/json", **cors_headers()},
    )


def error_response(message: str, status: int = 400) -> Response:
    return json_response({"error": message}, status=status)


# ---------------------------------------------------------------------------
# Chat handler
# ---------------------------------------------------------------------------
async def handle_chat(request, env) -> Response:
    try:
        body = await request.json()
    except Exception:
        return error_response("Invalid JSON body")

    user_message = body.get("message", "").strip()
    if not user_message:
        return error_response("'message' field is required")

    history = body.get("history", [])

    messages = [{"role": "system", "content": FAQ_CONTEXT}]
    for turn in history[-10:]:  # keep only the 10 most recent turns for context
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    ai_response = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {"messages": messages, "max_tokens": 512},
    )

    reply = (
        ai_response.get("response", "")
        if isinstance(ai_response, dict)
        else str(ai_response)
    )

    return json_response({"reply": reply, "model": "@cf/meta/llama-3.1-8b-instruct"})


# ---------------------------------------------------------------------------
# Security scan handler
# ---------------------------------------------------------------------------
async def handle_scan(request, env) -> Response:
    try:
        body = await request.json()
    except Exception:
        return error_response("Invalid JSON body")

    target = body.get("url", "").strip()
    if not target:
        return error_response("'url' field is required")

    scan_type = body.get("scan_type", "quick")

    depth_note = (
        "Provide a comprehensive deep-dive analysis."
        if scan_type == "full"
        else "Provide a concise quick-scan checklist."
    )

    messages = [
        {"role": "system", "content": SCAN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Analyse this target: {target}\n{depth_note}",
        },
    ]

    ai_response = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {"messages": messages, "max_tokens": 768},
    )

    raw = (
        ai_response.get("response", "")
        if isinstance(ai_response, dict)
        else str(ai_response)
    )

    # Attempt to parse AI JSON output; fall back to plain text wrapper
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        parsed = {"analysis": raw}

    return json_response(
        {"target": target, "scan_type": scan_type, "result": parsed}
    )


# ---------------------------------------------------------------------------
# MCP server handler
# ---------------------------------------------------------------------------
async def handle_mcp(request, env) -> Response:
    method = request.method.upper()

    # Discovery endpoint – return manifest
    if method == "GET":
        return json_response(MCP_MANIFEST)

    # Tool invocation
    if method == "POST":
        try:
            body = await request.json()
        except Exception:
            return error_response("Invalid JSON body")

        tool_name = body.get("tool")
        params = body.get("params", {})

        if tool_name == "chat":
            message = params.get("message", "")
            history = params.get("history", [])
            # Reuse chat logic by building a synthetic request-like object
            result = await _run_chat(env, message, history)
            return json_response({"tool": tool_name, "result": result})

        if tool_name == "scan_url":
            url = params.get("url", "")
            scan_type = params.get("scan_type", "quick")
            result = await _run_scan(env, url, scan_type)
            return json_response({"tool": tool_name, "result": result})

        if tool_name == "get_onboarding_guide":
            role = params.get("role", "contributor")
            result = _get_onboarding_guide(role)
            return json_response({"tool": tool_name, "result": result})

        return error_response(f"Unknown tool: {tool_name}", 404)

    return error_response("Method not allowed", 405)


# ---------------------------------------------------------------------------
# Internal helpers used by both direct API and MCP
# ---------------------------------------------------------------------------
async def _run_chat(env, message: str, history: list) -> dict:
    if not message:
        return {"error": "'message' is required"}
    messages = [{"role": "system", "content": FAQ_CONTEXT}]
    for turn in history[-10:]:  # keep only the 10 most recent turns for context
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    ai_response = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {"messages": messages, "max_tokens": 512},
    )
    reply = (
        ai_response.get("response", "")
        if isinstance(ai_response, dict)
        else str(ai_response)
    )
    return {"reply": reply}


async def _run_scan(env, url: str, scan_type: str = "quick") -> dict:
    if not url:
        return {"error": "'url' is required"}
    depth_note = (
        "Provide a comprehensive deep-dive analysis."
        if scan_type == "full"
        else "Provide a concise quick-scan checklist."
    )
    messages = [
        {"role": "system", "content": SCAN_SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyse this target: {url}\n{depth_note}"},
    ]
    ai_response = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {"messages": messages, "max_tokens": 768},
    )
    raw = (
        ai_response.get("response", "")
        if isinstance(ai_response, dict)
        else str(ai_response)
    )
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {"analysis": raw}


def _get_onboarding_guide(role: str) -> dict:
    guides = {
        "contributor": {
            "role": "contributor",
            "title": "Contributing to OWASP BLT",
            "steps": [
                "Fork https://github.com/OWASP-BLT/BLT and clone locally.",
                "Copy .env.example to .env and configure required credentials.",
                "Run `docker-compose up` to start the development environment.",
                "Browse to http://localhost:8000 and verify the app runs.",
                "Pick a good-first-issue on GitHub and comment to claim it.",
                "Create a feature branch, make your changes, and open a PR.",
                "Ensure all tests pass and your PR description is detailed.",
            ],
            "resources": {
                "contributing_guide": "https://github.com/OWASP-BLT/BLT/blob/main/CONTRIBUTING.md",
                "slack": "https://owasp.org/slack/invite",
                "issues": "https://github.com/OWASP-BLT/BLT/issues?q=is%3Aopen+label%3A%22good+first+issue%22",
            },
        },
        "bug_hunter": {
            "role": "bug_hunter",
            "title": "Getting Started as a Bug Hunter",
            "steps": [
                "Register a free account at https://www.bugheist.com.",
                "Browse the Domains or Projects section to find a target.",
                "Read the scope and rules for the target before testing.",
                "Find a bug and capture a clear screenshot or screen recording.",
                "Submit a detailed bug report including steps to reproduce.",
                "Earn points, badges, and SIZZLE token rewards.",
                "Climb the leaderboard and unlock new bounty opportunities.",
            ],
            "resources": {
                "platform": "https://www.bugheist.com",
                "leaderboard": "https://www.bugheist.com/leaderboard/",
            },
        },
        "organisation": {
            "role": "organisation",
            "title": "Registering Your Organisation on BLT",
            "steps": [
                "Create an account at https://www.bugheist.com.",
                "Navigate to 'Add Organisation' in your dashboard.",
                "Provide your domain, logo, and bug-bounty scope details.",
                "Set reward amounts (points, Bacon, or SIZZLE tokens).",
                "Review incoming bug reports and triage them promptly.",
                "Publish fixed issues to build community trust.",
            ],
            "resources": {
                "platform": "https://www.bugheist.com",
                "docs": "https://github.com/OWASP-BLT/BLT/wiki",
            },
        },
    }
    return guides.get(
        role,
        {"error": f"Unknown role '{role}'. Valid roles: contributor, bug_hunter, organisation"},
    )


# ---------------------------------------------------------------------------
# Main Worker entrypoint
# ---------------------------------------------------------------------------
class BltByte(WorkerEntrypoint):
    async def fetch(self, request) -> Response:
        url = request.url
        # Parse path from full URL
        try:
            path = "/" + "/".join(url.split("/")[3:]).split("?")[0].lstrip("/")
        except Exception:
            path = "/"

        method = request.method.upper()

        # Pre-flight CORS
        if method == "OPTIONS":
            return Response(
                "",
                status=204,
                headers=cors_headers(),
            )

        # Health check
        if path == "/api/health":
            return json_response({"status": "ok", "service": "blt-byte"})

        # Chat endpoint (API format)
        if path == "/api/chat" and method == "POST":
            return await handle_chat(request, self.env)

        # Simple chat endpoint for HTML frontend (POST to /)
        if path == "/" and method == "POST":
            return await self._handle_simple_chat(request)

        # Security scan endpoint
        if path == "/api/scan" and method == "POST":
            return await handle_scan(request, self.env)

        # MCP server endpoint
        if path == "/api/mcp":
            return await handle_mcp(request, self.env)

        # HTML serving routes (GET requests)
        if method == "GET":
            # Landing page
            if path in ("/", "/index.html"):
                return self._serve_html()
            
            # Chat page
            if path == "/chat":
                return self._serve_chat_html()
        
        # 404 for unknown API paths
        if path.startswith("/api/"):
            return error_response("Not found", 404)

        # All other routes: let Assets binding serve static files (logo, etc.)
        return await self.env.ASSETS.fetch(request)
    
    async def _handle_simple_chat(self, request) -> Response:
        """Handle chat for HTML frontend - uses simpler response format"""
        try:
            body = await request.json()
        except Exception:
            return error_response("Invalid JSON body")

        user_message = body.get("message", "").strip()
        if not user_message:
            return error_response("'message' field is required")

        # Use FAQ context for responses
        messages = [
            {"role": "system", "content": FAQ_CONTEXT},
            {"role": "user", "content": user_message}
        ]

        try:
            ai_response = await self.env.AI.run(
                "@cf/meta/llama-3.1-8b-instruct",
                {"messages": messages, "max_tokens": 512},
            )

            reply = (
                ai_response.get("response", "")
                if isinstance(ai_response, dict)
                else str(ai_response)
            )

            # Return format expected by HTML frontend
            return json_response({
                "success": True,
                "message": reply,
                "user_message": user_message
            })
        except Exception as e:
            return error_response(f"AI service error: {str(e)}", 500)
    
    def _serve_html(self) -> Response:
        """Serve the landing page HTML"""
        try:
            html_file = Path(__file__).parent / 'pages' / "index.html"
            html_content = html_file.read_text()
            return Response(
                html_content,
                status=200,
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "Cache-Control": "public, max-age=300",
                    **cors_headers()
                }
            )
        except FileNotFoundError:
            return error_response("HTML file not found", 404)
    
    def _serve_chat_html(self) -> Response:
        """Serve the chat page HTML"""
        try:
            html_file = Path(__file__).parent / 'pages' / "chat.html"
            html_content = html_file.read_text()
            return Response(
                html_content,
                status=200,
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "Cache-Control": "public, max-age=300",
                    **cors_headers()
                }
            )
        except FileNotFoundError:
            return error_response("Chat HTML file not found", 404)