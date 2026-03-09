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
import hashlib
import traceback
import pyodide
import js

from workers import Response, WorkerEntrypoint
from pyodide.ffi import JsProxy

# Enable deep debugging for proxy errors
try:
    pyodide.setDebug(True)
except Exception:
    pass # Debug mode not available in this Pyodide build

# ---------------------------------------------------------------------------
# BLT FAQ knowledge base
# ---------------------------------------------------------------------------
CLOUDFLARE_AI_MODEL = "@cf/openai/gpt-oss-120b"
FAQ_CONTEXT = """
You are Byte, the AI assistant for OWASP BLT (Bug Logging Tool), a gamified QA and vulnerability disclosure platform.

Key Information:
- Websites: https://www.bugheist.com, https://owasp.org/www-project-bug-logging-tool/
- GitHub: https://github.com/OWASP-BLT/BLT
- Features: Bug reporting, gamification (points, leaderboards), SIZZLE tokens, Bacon currency.
- Tech: Python/Django backend, Cloudflare Workers AI.
- Slack: #project-blt at https://owasp.org/slack/invite

Contributor Onboarding:
1. Fork & clone the BLT GitHub repo.
2. Setup .env from .env.example.
3. Run `docker-compose up` and visit http://localhost:8000.
4. Claim a 'good-first-issue' and submit a PR.

Bug Hunter Onboarding:
1. Register at https://www.bugheist.com.
2. Select a target, find bugs, and submit reports with screenshots.
3. Earn points and climb the leaderboard.

Capabilities:
- /api/scan: Header analysis, SSL/TLS checks, redirect detection, sensitive file checks.
- /api/mcp: search_bugs, submit_bug, get_leaderboard, scan_url.

Be concise, friendly, and security-focused. **DO NOT include any internal monologue, thought process, or "We should respond as..." meta-commentary. Respond only as Byte speaking to the user.**
"""

SCAN_SYSTEM_PROMPT = """
You are a security analysis assistant for OWASP BLT. Given a URL or domain,
provide a structured security assessment. **Respond ONLY with the final analysis. Do not include internal reasoning or thought processes.**
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
        # Avoid JsProxy for inputs by using text() + native json.loads()
        body_text = await request.text()
        body = json.loads(body_text) if body_text else {}
    except Exception:
        return error_response("Invalid JSON body")
    if not isinstance(body, dict):
        return error_response("JSON body must be an object")

    user_message = body.get("message", "").strip()
    if not user_message:
        return error_response("'message' field is required")

    history = body.get("history", [])
    result = await _run_chat(env, user_message, history)
    
    if "error" in result:
        return error_response(result["error"], int(result.get("status", 502)))
        
    return json_response({**result, "model": CLOUDFLARE_AI_MODEL})


# ---------------------------------------------------------------------------
# Security scan handler
# ---------------------------------------------------------------------------
async def handle_scan(request, env) -> Response:
    try:
        # Avoid JsProxy for inputs by using text() + native json.loads()
        body_text = await request.text()
        body = json.loads(body_text) if body_text else {}
    except Exception:
        return error_response("Invalid JSON body")
    if not isinstance(body, dict):
        return error_response("JSON body must be an object")

    target = body.get("url", "").strip()
    if not target:
        return error_response("'url' field is required")

    scan_type = body.get("scan_type", "quick")
    if scan_type not in ("quick", "full"):
        return error_response("Invalid 'scan_type'. Allowed values: quick, full", 400)

    result = await _run_scan(env, target, scan_type)
    if "error" in result:
        return error_response(result["error"], 502)
    return json_response({"target": target, "scan_type": scan_type, "result": result})


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
            body_text = await request.text()
            body = json.loads(body_text) if body_text else {}
        except Exception:
            return error_response("Invalid JSON body")
        if not isinstance(body, dict):
            return error_response("JSON body must be an object")

        tool_name = body.get("tool")
        params = body.get("params", {})
        if not isinstance(params, dict):
            return error_response("'params' must be an object", 400)

        if tool_name == "chat":
            message = params.get("message", "")
            history = params.get("history", [])
            # Reuse chat logic by building a synthetic request-like object
            result = await _run_chat(env, message, history)
            return json_response({"tool": tool_name, "result": result})

        if tool_name == "scan_url":
            url = params.get("url", "")
            scan_type = params.get("scan_type", "quick")
            if scan_type not in ("quick", "full"):
                return error_response("Invalid 'scan_type'. Allowed values: quick, full", 400)
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
        return {"error": "'message' is required", "status": 400}
    if history is None:
        history = []
    if not isinstance(history, list):
        return {"error": "'history' must be an array", "status": 400}
    
    # Build message array for better model performance
    messages = [
        {"role": "system", "content": FAQ_CONTEXT}
    ]
    
    # Add conversation history
    history_list = list(history[-10:]) if history else []
    for turn in history_list:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role", ""))
        content = str(turn.get("content", ""))
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    
    # Add current user message
    messages.append({"role": "user", "content": message})
    
            # Call Cloudflare AI using JS serialization to avoid proxy issues
    try:
        # Convert Python options to pure JS to avoid proxy errors
        ai_options = js.JSON.parse(json.dumps({
            "messages": messages,
            "max_tokens": 2048  # Give the model enough room to finish thinking AND answer
        }))
        
        raw_ai_response = await env.AI.run(
            CLOUDFLARE_AI_MODEL,
            ai_options
        )
        
        # NUCLEAR EXTRACTION: Convert JS Result to pure Python tree via JSON bridge
        # This is the only 100% reliable way to avoid nested "borrowed proxy" issues.
        ai_response = json.loads(js.JSON.stringify(raw_ai_response))
        
        print(f"AI Response Keys: {list(ai_response.keys()) if isinstance(ai_response, dict) else 'Not a dict'}")
            
        reply = None

        # 1. Handle OpenAI-compatible format (choices[0].message.content)
        if isinstance(ai_response, dict) and 'choices' in ai_response:
            choices = ai_response['choices']
            if isinstance(choices, list) and len(choices) > 0:
                choice = choices[0]
                if isinstance(choice, dict):
                    msg = choice.get('message', {})
                    if isinstance(msg, dict):
                        # ONLY pick up 'content'. Do NOT show 'reasoning_content' (thought process) to the user.
                        reply = msg.get('content')

        # 2. Handle standard Workers AI format (output or response)
        if reply is None:
            response_output = ai_response.get('output') if isinstance(ai_response, dict) else ai_response
            
            if isinstance(response_output, list):
                for item in response_output:
                    if isinstance(item, dict) and item.get('role') == 'assistant':
                        content = item.get('content', [])
                        if isinstance(content, list):
                            for content_item in content:
                                if isinstance(content_item, dict) and content_item.get('type') == 'output_text':
                                    reply = content_item.get('text')
                                    break
                        elif isinstance(content, str):
                            reply = content
                        break
            elif isinstance(response_output, str):
                reply = response_output
            elif isinstance(response_output, dict):
                reply = (
                    response_output.get('response') or 
                    response_output.get('reply') or 
                    response_output.get('text') or 
                    response_output.get('content')
                )
            
        if reply is None:
            if isinstance(ai_response, dict):
                response_keys = list(ai_response.keys())
            else:
                response_keys = []

            try:
                response_dump = json.dumps(ai_response, sort_keys=True, default=str)
            except Exception:
                response_dump = str(type(ai_response))

            response_hash = hashlib.sha256(response_dump.encode("utf-8")).hexdigest()
            print(
                "AI fallback extraction needed. "
                f"response_type={type(ai_response).__name__} "
                f"response_len={len(response_dump)} "
                f"response_keys={response_keys[:10]} "
                f"response_sha256={response_hash}"
            )
            reply = "I received a response but couldn't parse the text. Please check the logs."
            
    except Exception as ai_error:
        print(f"AI call crash: {ai_error!s}")
        traceback.print_exc()
        return {
            "error": "The AI service is temporarily unavailable. Please try again.",
            "status": 502,
        }
    
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
    # Call Cloudflare AI using JS serialization to avoid proxy issues
    try:
        ai_options = js.JSON.parse(json.dumps({"messages": messages, "max_tokens": 768}))
        
        raw_ai_response = await env.AI.run(
            CLOUDFLARE_AI_MODEL,
            ai_options
        )
        
        # Nuclear conversion
        ai_response = json.loads(js.JSON.stringify(raw_ai_response))
    except Exception as ai_error:
        print(f"AI scan call crash: {ai_error!s}")
        traceback.print_exc()
        return {"error": "The AI service is temporarily unavailable. Please try again."}

    reply = None
    # 1. OpenAI-style
    if isinstance(ai_response, dict) and 'choices' in ai_response:
        choices = ai_response['choices']
        if isinstance(choices, list) and len(choices) > 0:
            choice = choices[0]
            if isinstance(choice, dict):
                msg = choice.get('message', {})
                if isinstance(msg, dict):
                    # Only final content
                    reply = msg.get('content')

    # 2. Standard style
    if reply is None:
        output = ai_response.get("response") or ai_response.get("output") if isinstance(ai_response, dict) else ai_response
        reply = str(output) if output is not None else ""

    try:
        return json.loads(reply)
    except (json.JSONDecodeError, ValueError):
        return {"analysis": reply}


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
class Default(WorkerEntrypoint):
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

        # Security scan endpoint
        if path == "/api/scan" and method == "POST":
            return await handle_scan(request, self.env)

        # MCP server endpoint
        if path == "/api/mcp":
            return await handle_mcp(request, self.env)

        # HTML serving routes (GET requests)
        if method == "GET":
            # Serve top-level HTML through the static assets binding.
            if path in ("/", "/index.html"):
                request_url = str(request.url)
                if path == "/":
                    request_url = request_url.rstrip("/") + "/index.html"
                return await self.env.ASSETS.fetch(request_url)
            
            # Chat page
            if path == "/chat":
                request_url = str(request.url).rstrip("/") + "/chat.html"
                return await self.env.ASSETS.fetch(request_url)
        
        # 404 for unknown API paths
        if path.startswith("/api/"):
            return error_response("Not found", 404)

        # All other routes: let Assets binding serve static files (logo, etc.)
        return await self.env.ASSETS.fetch(request)