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
import re
import traceback
try:
    import pyodide
    import js
except ImportError:
    # Local testing environment
    pyodide = None
    js = None
import time

from workers import Response, WorkerEntrypoint

# Security constants
MAX_INPUT_LENGTH = 2000
MAX_URL_LENGTH = 500
RATE_LIMIT_INTERVAL = 1.0  # seconds
IP_RATE_LIMITS = {}
RATE_LIMIT_MAX_KEYS = 10000
RATE_LIMIT_TTL = 60.0

# Production mode: Disable deep debugging
try:
    pyodide.setDebug(False)
except AttributeError:
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
                        "description": "User role. Valid values: contributor, bug_hunter, organisation.",
                        "default": "contributor",
                    }
                },
                "required": [],
            },
        },
    ],
}


def get_ai_model(env) -> str:
    """Return the configured AI model or a default."""
    if hasattr(env, "CLOUDFLARE_AI_MODEL") and env.CLOUDFLARE_AI_MODEL:
        return str(env.CLOUDFLARE_AI_MODEL)
    return CLOUDFLARE_AI_MODEL


def is_rate_limited(request) -> bool:
    """Basic IP-based rate limiting using an in-memory dictionary.
    Fails closed (returns True) on exception for security.
    """
    try:
        headers = getattr(request, "headers", None)
        if headers is None:
            return True
        
        ip = headers.get("cf-connecting-ip") or "unknown"
        now = time.time()
        
        if len(IP_RATE_LIMITS) > RATE_LIMIT_MAX_KEYS:
            cutoff = now - RATE_LIMIT_TTL
            stale_keys = [k for k, ts in IP_RATE_LIMITS.items() if ts < cutoff]
            for k in stale_keys:
                IP_RATE_LIMITS.pop(k, None)
        
        last_request_time = IP_RATE_LIMITS.get(ip, 0)
        
        if now - last_request_time < RATE_LIMIT_INTERVAL:
            return True
        
        IP_RATE_LIMITS[ip] = now
        return False
    except (AttributeError, TypeError) as e:
        print(f"Error in is_rate_limited: {e}")
        return True


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
    if is_rate_limited(request):
        return error_response("Too many requests", 429)

    # Avoid JsProxy for inputs by using text() + native json.loads()
    body_text = await request.text()
    try:
        body = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        return error_response("Invalid JSON body")
    if not isinstance(body, dict):
        return error_response("JSON body must be an object")

    user_message = body.get("message", "")
    if not isinstance(user_message, str):
        return error_response("'message' field must be a string")
    if len(user_message) > MAX_INPUT_LENGTH:
        return error_response(f"Message too long (max {MAX_INPUT_LENGTH} chars)")

    user_message = user_message.strip()
    if not user_message:
        return error_response("'message' field is required")

    history = body.get("history", [])
    result = await _run_chat(env, user_message, history)
    
    if "error" in result:
        return error_response(result["error"], int(result.get("status", 502)))
        
    return json_response({**result, "model": get_ai_model(env)})


# ---------------------------------------------------------------------------
# Security scan handler
# ---------------------------------------------------------------------------
async def handle_scan(request, env) -> Response:
    if is_rate_limited(request):
        return error_response("Too many requests", 429)

    # Avoid JsProxy for inputs by using text() + native json.loads()
    body_text = await request.text()
    try:
        body = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        return error_response("Invalid JSON body")
    if not isinstance(body, dict):
        return error_response("JSON body must be an object")

    target = body.get("url", "")
    if not isinstance(target, str):
        return error_response("'url' field must be a string")
    if len(target) > MAX_URL_LENGTH:
        return error_response(f"URL too long (max {MAX_URL_LENGTH} chars)")

    target = target.strip()
    if not target:
        return error_response("'url' field is required")

    scan_type = body.get("scan_type", "quick")
    if scan_type not in ("quick", "full"):
        return error_response("Invalid 'scan_type'. Allowed values: quick, full", 400)

    result = await _run_scan(env, target, scan_type)
    if "error" in result:
        return error_response(result["error"], int(result.get("status", 502)))
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
        if is_rate_limited(request):
            return error_response("Too many requests", 429)

        body_text = await request.text()
        try:
            body = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            return error_response("Invalid JSON body")
        if not isinstance(body, dict):
            return error_response("JSON body must be an object")

        tool_name = body.get("tool")
        if not isinstance(tool_name, str) or not tool_name.strip():
            return error_response("'tool' must be a non-empty string", 400)
        tool_name = tool_name.strip()
        params = body.get("params", {})
        if not isinstance(params, dict):
            return error_response("'params' must be an object", 400)

        if tool_name == "chat":
            message = params.get("message", "")
            if not isinstance(message, str) or not message.strip():
                return error_response("'message' must be a non-empty string", 400)
            
            if len(message) > MAX_INPUT_LENGTH:
                return error_response(f"Message too long (max {MAX_INPUT_LENGTH} chars)")
                
            history = params.get("history", [])
            # Reuse chat logic by building a synthetic request-like object
            result = await _run_chat(env, message, history)
            if "error" in result:
                return error_response(result["error"], int(result.get("status", 502)))
            return json_response({"tool": tool_name, "result": result})

        if tool_name == "scan_url":
            url = params.get("url", "")
            if not isinstance(url, str) or not url.strip():
                return error_response("'url' must be a non-empty string", 400)
            
            if len(url) > MAX_URL_LENGTH:
                return error_response(f"URL too long (max {MAX_URL_LENGTH} chars)")
            scan_type = params.get("scan_type", "quick")
            if scan_type not in ("quick", "full"):
                return error_response("Invalid 'scan_type'. Allowed values: quick, full", 400)
            result = await _run_scan(env, url, scan_type)
            if "error" in result:
                return error_response(result["error"], int(result.get("status", 502)))
            return json_response({"tool": tool_name, "result": result})

        if tool_name == "get_onboarding_guide":
            role = params.get("role", "contributor")
            if not isinstance(role, str):
                return error_response("'role' must be a string", 400)
            if role not in ("contributor", "bug_hunter", "organisation"):
                return error_response(
                    "Invalid 'role'. Allowed values: contributor, bug_hunter, organisation",
                    400,
                )
            result = _get_onboarding_guide(role)
            return json_response({"tool": tool_name, "result": result})

        return error_response(f"Unknown tool: {tool_name}", 404)

    return error_response("Method not allowed", 405)


# ---------------------------------------------------------------------------
# Internal helpers used by both direct API and MCP
# ---------------------------------------------------------------------------
def _sanitize_ai_output(text: str) -> str | None:
    """Strip internal reasoning wrappers/preambles from model output."""

    cleaned = text

    # Remove common hidden-thought block wrappers first.
    cleaned = re.sub(r"(?is)<think\b[^>]*>.*?</think>", " ", cleaned)
    cleaned = re.sub(r"(?is)<reasoning\b[^>]*>.*?</reasoning>", " ", cleaned)
    cleaned = re.sub(r"(?is)<analysis\b[^>]*>.*?</analysis>", " ", cleaned)

    # Remove specific reasoning tags only. Avoid broad regex that strips all XML-like tags.
    # We explicitly preserve common formatting or structural tags that might be in the markdown.
    cleaned = re.sub(r"(?is)</?(?:think|reasoning|analysis|thought|brain|monologue)\b[^>]*>", " ", cleaned)

    # Drop common reasoning preambles at the beginning.
    cleaned = re.sub(
        r"(?im)^\s*(?:reasoning|analysis|thought process|chain\s*of\s*thought|internal reasoning)\s*:\s*",
        "",
        cleaned,
    )

    cleaned = cleaned.strip()
    return cleaned or None


def _extract_ai_text(ai_response) -> str | None:
    """Normalize text extraction across Cloudflare/OpenAI-style responses."""

    # 1) OpenAI-compatible shape: choices[0].message.content
    if isinstance(ai_response, dict):
        choices = ai_response.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, list):
                        parts = []
                        for item in content:
                            if not isinstance(item, dict):
                                continue
                            if item.get("type") not in ("text", "output_text"):
                                continue
                            text = item.get("text")
                            if isinstance(text, str) and text:
                                parts.append(text)
                        if parts:
                            return _sanitize_ai_output("\n".join(parts))
                    if isinstance(content, str):
                        return _sanitize_ai_output(content)

    # 2) Prefer explicit output payload, then response payload, then raw response
    payload = ai_response
    if isinstance(ai_response, dict):
        if "output" in ai_response:
            payload = ai_response["output"]
        elif ai_response.get("response") is not None:
            payload = ai_response.get("response")

    # 3) List-style output: find assistant item and extract content
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict) or item.get("role") != "assistant":
                continue
            content = item.get("content")
            if isinstance(content, str):
                return _sanitize_ai_output(content)
            if isinstance(content, list):
                parts = []
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") not in ("text", "output_text"):
                        continue
                    text = part.get("text")
                    if isinstance(text, str) and text:
                        parts.append(text)
                if parts:
                    return _sanitize_ai_output("\n".join(parts))
        return None

    # 4) Dict/str outputs
    if isinstance(payload, dict):
        for key in ("response", "reply", "text", "content"):
            value = payload.get(key)
            if isinstance(value, str):
                return _sanitize_ai_output(value)
        return None

    if isinstance(payload, str):
        return _sanitize_ai_output(payload)

    return None


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
            get_ai_model(env),
            ai_options
        )
        
        # NUCLEAR EXTRACTION: Convert JS Result to pure Python tree via JSON bridge
        # This is the only 100% reliable way to avoid nested "borrowed proxy" issues.
        ai_response = json.loads(js.JSON.stringify(raw_ai_response))
        
        print(f"AI Response Keys: {list(ai_response.keys()) if isinstance(ai_response, dict) else 'Not a dict'}")
            
        # Shared extraction logic keeps chat/scan behavior consistent.
        reply = _extract_ai_text(ai_response)
            
        if reply is None:
            if isinstance(ai_response, dict):
                response_keys = list(ai_response.keys())
            else:
                response_keys = []

            try:
                response_dump = json.dumps(ai_response, sort_keys=True, default=str)
            except (TypeError, ValueError):
                response_dump = str(type(ai_response))

            response_hash = hashlib.sha256(response_dump.encode("utf-8")).hexdigest()
            print(
                "AI fallback extraction needed. "
                f"response_type={type(ai_response).__name__} "
                f"response_len={len(response_dump)} "
                f"response_keys={response_keys[:10]} "
                f"response_sha256={response_hash}"
            )
            return {
                "error": "The AI service returned an unsupported response format. Please try again.",
                "status": 502,
            }
            
    except Exception as ai_error:
        print(f"AI call crash: {ai_error!s}")
        if "remote" in str(ai_error).lower():
            print("[info] AI service requires remote run. Falling back to mock response for local testing.")
            return {"reply": "Byte: (Local Dev Mode) Hello! I see you're testing locally. The AI service requires a remote connection, but I'm here to help with your development tests!"}
            
        traceback.print_exc()
        return {
            "error": f"AI service error: {ai_error}",
            "status": 502,
        }
    
    return {"reply": reply}


async def _run_scan(env, url: str, scan_type: str = "quick") -> dict:
    if not url:
        return {"error": "'url' is required", "status": 400}
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
            get_ai_model(env),
            ai_options
        )
        
        # Nuclear conversion
        ai_response = json.loads(js.JSON.stringify(raw_ai_response))
    except (AttributeError, TypeError, ValueError, RuntimeError) as ai_error:
        print(f"AI scan call crash: {ai_error!s}")
        traceback.print_exc()
        return {"error": "The AI service is temporarily unavailable. Please try again.", "status": 502}

    reply = _extract_ai_text(ai_response)
    if reply is None:
        return {"error": "The AI service returned an unsupported response format.", "status": 502}

    try:
        data = json.loads(reply)
        # Ensure minimal schema compliance even on partial JSON
        if not isinstance(data, dict):
             return {"headers_to_check": [], "vulnerabilities_to_test": [], "blt_categories": [], "notes": reply}
        return data
    except (json.JSONDecodeError, ValueError):
        # Prevent schema downgrade: wrap raw text in the expected JSON structure
        return {
            "headers_to_check": [],
            "vulnerabilities_to_test": [],
            "blt_categories": [],
            "notes": reply
        }


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
class Default(WorkerEntrypoint):
    async def on_fetch(self, request, env=None, ctx=None) -> Response:
        try:
            url_str = str(request.url)
            method = request.method.upper()
            # Parse path from full URL
            try:
                path = "/" + "/".join(url_str.split("/")[3:]).split("?")[0].lstrip("/")
            except Exception as e:
                print(f"[error] Path parsing failed for {url_str}: {e}")
                path = "/"
            
            print(f"Request: {method} {path}")
            

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
                origin = "/".join(str(request.url).split("/", 3)[:3])
                # Serve top-level HTML through the static assets binding.
                if path in ("/", "/index.html"):
                    request_url = (
                        origin + "/index.html"
                        if path == "/"
                        else str(request.url).split("?", 1)[0]
                    )
                    return await self.env.ASSETS.fetch(request_url)
                
                # Chat page
                if path in ("/chat", "/chat/"):
                    request_url = origin + "/chat.html"
                    return await self.env.ASSETS.fetch(request_url)
            
            # 404 for unknown API paths
            if path.startswith("/api/"):
                return error_response("Not found", 404)

            # All other routes: let Assets binding serve static files (logo, etc.)
            try:
                return await self.env.ASSETS.fetch(request)
            except Exception as e:
                print(f"[error] ASSETS fetch failed: {e}")
                traceback.print_exc()
                return error_response("Asset fetch failed", 500)
        except Exception as e:
            print(f"[critical error] fetch crashed: {e}")
            traceback.print_exc()
            return error_response(f"Internal Server Error: {e}", 500)