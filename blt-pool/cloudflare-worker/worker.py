"""BLT GitHub App — Python Cloudflare Worker.

Handles GitHub webhooks and serves a landing homepage.
This is the Python / Cloudflare Workers port of the original Node.js Probot app.

Entry point: ``on_fetch(request, env)`` — called by the Cloudflare runtime for
every incoming HTTP request.

Environment variables / secrets (configure via ``wrangler.toml`` or
``wrangler secret put``):
    APP_ID             — GitHub App numeric ID
    PRIVATE_KEY        — GitHub App RSA private key (PEM, PKCS#1 or PKCS#8)
    WEBHOOK_SECRET     — GitHub App webhook secret
    GITHUB_APP_SLUG    — GitHub App slug used to build the install URL
    BLT_API_URL        — BLT API base URL (default: https://blt-api.owasp-blt.workers.dev)
    GITHUB_CLIENT_ID   — OAuth client ID (optional)
    GITHUB_CLIENT_SECRET — OAuth client secret (optional)
"""

import base64
import hashlib
import hmac as _hmac
import json
import time
from urllib.parse import urlparse

from js import Headers, Response, console, fetch  # Cloudflare Workers JS bindings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ASSIGN_COMMAND = "/assign"
UNASSIGN_COMMAND = "/unassign"
MAX_ASSIGNEES = 3
ASSIGNMENT_DURATION_HOURS = 24
BUG_LABELS = {"bug", "vulnerability", "security"}

# DER OID sequence for rsaEncryption (used when wrapping PKCS#1 → PKCS#8)
_RSA_OID_SEQ = bytes([
    0x30, 0x0D,
    0x06, 0x09, 0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x01, 0x01,
    0x05, 0x00,
])

# ---------------------------------------------------------------------------
# DER / PEM helpers (needed for PKCS#1 → PKCS#8 conversion)
# ---------------------------------------------------------------------------


def _der_len(n: int) -> bytes:
    """Encode a DER length field."""
    if n < 0x80:
        return bytes([n])
    if n < 0x100:
        return bytes([0x81, n])
    return bytes([0x82, (n >> 8) & 0xFF, n & 0xFF])


def _wrap_pkcs1_as_pkcs8(pkcs1_der: bytes) -> bytes:
    """Wrap a PKCS#1 RSAPrivateKey DER blob into a PKCS#8 PrivateKeyInfo."""
    version = bytes([0x02, 0x01, 0x00])  # INTEGER 0
    octet = bytes([0x04]) + _der_len(len(pkcs1_der)) + pkcs1_der
    content = version + _RSA_OID_SEQ + octet
    return bytes([0x30]) + _der_len(len(content)) + content


def pem_to_pkcs8_der(pem: str) -> bytes:
    """Convert a PEM private key (PKCS#1 or PKCS#8) to PKCS#8 DER bytes.

    GitHub App private keys are usually PKCS#1 (``BEGIN RSA PRIVATE KEY``).
    SubtleCrypto's ``importKey`` requires PKCS#8, so we wrap if necessary.
    """
    lines = pem.strip().splitlines()
    is_pkcs1 = lines[0].strip() == "-----BEGIN RSA PRIVATE KEY-----"
    b64 = "".join(line for line in lines if not line.startswith("-----"))
    der = base64.b64decode(b64)
    return _wrap_pkcs1_as_pkcs8(der) if is_pkcs1 else der


# ---------------------------------------------------------------------------
# Base64url encoding
# ---------------------------------------------------------------------------


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Return True when the X-Hub-Signature-256 header matches the payload."""
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + _hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return _hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# JWT creation via SubtleCrypto (no external packages required)
# ---------------------------------------------------------------------------


async def create_github_jwt(app_id: str, private_key_pem: str) -> str:
    """Create a signed GitHub App JWT using the Web Crypto SubtleCrypto API."""
    from js import Uint8Array, crypto  # noqa: PLC0415 — runtime import

    now = int(time.time())
    header_b64 = _b64url(
        json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload_b64 = _b64url(
        json.dumps(
            {"iat": now - 60, "exp": now + 600, "iss": str(app_id)},
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header_b64}.{payload_b64}"

    # Import private key into SubtleCrypto
    pkcs8_der = pem_to_pkcs8_der(private_key_pem)
    key_array = Uint8Array.new(len(pkcs8_der))
    for i, b in enumerate(pkcs8_der):
        key_array[i] = b

    crypto_key = await crypto.subtle.importKey(
        "pkcs8",
        key_array.buffer,
        {"name": "RSASSA-PKCS1-v1_5", "hash": "SHA-256"},
        False,
        ["sign"],
    )

    # Sign the JWT header.payload
    msg_bytes = signing_input.encode("ascii")
    msg_array = Uint8Array.new(len(msg_bytes))
    for i, b in enumerate(msg_bytes):
        msg_array[i] = b

    sig_buf = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", crypto_key, msg_array.buffer)
    sig_bytes = bytes(Uint8Array.new(sig_buf))
    return f"{signing_input}.{_b64url(sig_bytes)}"


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def _gh_headers(token: str) -> Headers:
    return Headers.new({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "BLT-GitHub-App/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }.items())


async def github_api(method: str, path: str, token: str, body=None):
    """Make an authenticated request to the GitHub REST API."""
    url = f"https://api.github.com{path}"
    kwargs = {"method": method, "headers": _gh_headers(token)}
    if body is not None:
        kwargs["body"] = json.dumps(body)
    return await fetch(url, **kwargs)


async def get_installation_token(
    installation_id: int, app_id: str, private_key: str
) -> str | None:
    """Exchange a GitHub App JWT for an installation access token."""
    jwt = await create_github_jwt(app_id, private_key)
    resp = await fetch(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        method="POST",
        headers=Headers.new({
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "BLT-GitHub-App/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }.items()),
    )
    if resp.status != 201:
        console.error(f"[BLT] Failed to get installation token: {resp.status}")
        return None
    data = json.loads(await resp.text())
    return data.get("token")


async def create_comment(
    owner: str, repo: str, number: int, body: str, token: str
) -> None:
    """Post a comment on a GitHub issue or pull request."""
    await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/{number}/comments",
        token,
        {"body": body},
    )


# ---------------------------------------------------------------------------
# BLT API helper
# ---------------------------------------------------------------------------


async def report_bug_to_blt(blt_api_url: str, issue_data: dict):
    """Report a bug to the BLT API; returns the created bug object or None."""
    try:
        payload = {
            "url": issue_data.get("url") or issue_data.get("github_url"),
            "description": issue_data.get("description", ""),
            "github_url": issue_data.get("github_url", ""),
            "label": issue_data.get("label", "general"),
            "status": "open",
        }
        resp = await fetch(
            f"{blt_api_url}/bugs",
            method="POST",
            headers=Headers.new({"Content-Type": "application/json"}.items()),
            body=json.dumps(payload),
        )
        data = json.loads(await resp.text())
        return data.get("data") if data.get("success") else None
    except Exception as exc:
        console.error(f"[BLT] Failed to report bug: {exc}")
        return None


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _is_human(user: dict) -> bool:
    """Return True for human GitHub users (not bots or apps).

    'Mannequin' is a placeholder user type GitHub assigns to contributions
    imported from external version-control systems (e.g. SVN migrations).
    """
    return bool(user and user.get("type") in ("User", "Mannequin"))


# ---------------------------------------------------------------------------
# Event handlers — mirror the Node.js handler logic exactly
# ---------------------------------------------------------------------------


async def handle_issue_comment(payload: dict, token: str) -> None:
    comment = payload["comment"]
    issue = payload["issue"]
    if not _is_human(comment["user"]):
        return
    body = comment["body"].strip()
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    login = comment["user"]["login"]
    if body.startswith(ASSIGN_COMMAND):
        await _assign(owner, repo, issue, login, token)
    elif body.startswith(UNASSIGN_COMMAND):
        await _unassign(owner, repo, issue, login, token)


async def _assign(
    owner: str, repo: str, issue: dict, login: str, token: str
) -> None:
    num = issue["number"]
    if issue.get("pull_request"):
        await create_comment(
            owner, repo, num,
            f"@{login} This command only works on issues, not pull requests.",
            token,
        )
        return
    if issue["state"] == "closed":
        await create_comment(
            owner, repo, num,
            f"@{login} This issue is already closed and cannot be assigned.",
            token,
        )
        return
    assignees = [a["login"] for a in issue.get("assignees", [])]
    if login in assignees:
        await create_comment(
            owner, repo, num,
            f"@{login} You are already assigned to this issue.",
            token,
        )
        return
    if len(assignees) >= MAX_ASSIGNEES:
        await create_comment(
            owner, repo, num,
            f"@{login} This issue already has the maximum number of assignees "
            f"({MAX_ASSIGNEES}). Please work on a different issue.",
            token,
        )
        return
    await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/{num}/assignees",
        token,
        {"assignees": [login]},
    )
    deadline = time.strftime(
        "%a, %d %b %Y %H:%M:%S UTC",
        time.gmtime(time.time() + ASSIGNMENT_DURATION_HOURS * 3600),
    )
    await create_comment(
        owner, repo, num,
        f"@{login} You have been assigned to this issue! 🎉\n\n"
        f"Please submit a pull request within **{ASSIGNMENT_DURATION_HOURS} hours** "
        f"(by {deadline}).\n\n"
        f"If you need more time or cannot complete the work, please comment "
        f"`{UNASSIGN_COMMAND}` so others can pick it up.\n\n"
        "Happy coding! 🚀 — [OWASP BLT](https://owaspblt.org)",
        token,
    )


async def _unassign(
    owner: str, repo: str, issue: dict, login: str, token: str
) -> None:
    num = issue["number"]
    assignees = [a["login"] for a in issue.get("assignees", [])]
    if login not in assignees:
        await create_comment(
            owner, repo, num,
            f"@{login} You are not currently assigned to this issue.",
            token,
        )
        return
    await github_api(
        "DELETE",
        f"/repos/{owner}/{repo}/issues/{num}/assignees",
        token,
        {"assignees": [login]},
    )
    await create_comment(
        owner, repo, num,
        f"@{login} You have been unassigned from this issue. "
        "Thanks for letting us know! 👍\n\n"
        "The issue is now open for others to pick up.",
        token,
    )


async def handle_issue_opened(
    payload: dict, token: str, blt_api_url: str
) -> None:
    issue = payload["issue"]
    sender = payload["sender"]
    if not _is_human(sender):
        return
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    labels = [lb["name"].lower() for lb in issue.get("labels", [])]
    is_bug = any(lb in BUG_LABELS for lb in labels)
    msg = (
        f"👋 Thanks for opening this issue, @{sender['login']}!\n\n"
        "Our team will review it shortly. In the meantime:\n"
        "- If you'd like to work on this issue, comment `/assign` to get assigned.\n"
        "- Visit [OWASP BLT](https://owaspblt.org) for more information about "
        "our bug bounty platform.\n"
    )
    if is_bug:
        bug_data = await report_bug_to_blt(blt_api_url, {
            "url": issue["html_url"],
            "description": issue["title"],
            "github_url": issue["html_url"],
            "label": labels[0] if labels else "bug",
        })
        if bug_data and bug_data.get("id"):
            msg += (
                "\n🐛 This issue has been automatically reported to "
                "[OWASP BLT](https://owaspblt.org) "
                f"(Bug ID: #{bug_data['id']}). "
                "Thank you for helping improve security!\n"
            )
    await create_comment(owner, repo, issue["number"], msg, token)


async def handle_issue_labeled(
    payload: dict, token: str, blt_api_url: str
) -> None:
    issue = payload["issue"]
    label = payload.get("label") or {}
    label_name = label.get("name", "").lower()
    if label_name not in BUG_LABELS:
        return
    all_labels = [lb["name"].lower() for lb in issue.get("labels", [])]
    # Only report the first time a bug label is added (avoid duplicates)
    if any(lb in BUG_LABELS for lb in all_labels if lb != label_name):
        return
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    bug_data = await report_bug_to_blt(blt_api_url, {
        "url": issue["html_url"],
        "description": issue["title"],
        "github_url": issue["html_url"],
        "label": label.get("name", "bug"),
    })
    if bug_data and bug_data.get("id"):
        await create_comment(
            owner, repo, issue["number"],
            f"🐛 This issue has been reported to [OWASP BLT](https://owaspblt.org) "
            f"(Bug ID: #{bug_data['id']}) after being labeled as "
            f"`{label.get('name', 'bug')}`.",
            token,
        )


async def handle_pull_request_opened(payload: dict, token: str) -> None:
    pr = payload["pull_request"]
    sender = payload["sender"]
    if not _is_human(sender):
        return
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    body = (
        f"👋 Thanks for opening this pull request, @{sender['login']}!\n\n"
        "**Before your PR is reviewed, please ensure:**\n"
        "- [ ] Your code follows the project's coding style and guidelines.\n"
        "- [ ] You have written or updated tests for your changes.\n"
        "- [ ] The commit messages are clear and descriptive.\n"
        "- [ ] You have linked any relevant issues (e.g., `Closes #123`).\n\n"
        "🔍 Our team will review your PR shortly. "
        "If you have questions, feel free to ask in the comments.\n\n"
        "🚀 Keep up the great work! — [OWASP BLT](https://owaspblt.org)"
    )
    await create_comment(owner, repo, pr["number"], body, token)


async def handle_pull_request_closed(payload: dict, token: str) -> None:
    pr = payload["pull_request"]
    sender = payload["sender"]
    if not pr.get("merged"):
        return
    if not _is_human(sender):
        return
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    body = (
        f"🎉 PR merged! Thanks for your contribution, @{pr['user']['login']}!\n\n"
        "Your work is now part of the project. Keep contributing to "
        "[OWASP BLT](https://owaspblt.org) and help make the web a safer place! 🛡️"
    )
    await create_comment(owner, repo, pr["number"], body, token)


# ---------------------------------------------------------------------------
# Webhook dispatcher
# ---------------------------------------------------------------------------


async def handle_webhook(request, env) -> Response:
    """Verify the GitHub webhook signature and route to the correct handler."""
    body_text = await request.text()
    payload_bytes = body_text.encode("utf-8")

    signature = request.headers.get("X-Hub-Signature-256") or ""
    secret = getattr(env, "WEBHOOK_SECRET", "")
    if secret and not verify_signature(payload_bytes, signature, secret):
        return _json({"error": "Invalid signature"}, 401)

    try:
        payload = json.loads(body_text)
    except Exception:
        return _json({"error": "Invalid JSON"}, 400)

    event = request.headers.get("X-GitHub-Event", "")
    action = payload.get("action", "")
    installation_id = (payload.get("installation") or {}).get("id")

    app_id = getattr(env, "APP_ID", "")
    private_key = getattr(env, "PRIVATE_KEY", "")
    token = None
    if installation_id and app_id and private_key:
        token = await get_installation_token(installation_id, app_id, private_key)

    if not token:
        console.error("[BLT] Could not obtain installation token")
        return _json({"error": "Authentication failed"}, 500)

    blt_api_url = getattr(env, "BLT_API_URL", "https://blt-api.owasp-blt.workers.dev")

    try:
        if event == "issue_comment" and action == "created":
            await handle_issue_comment(payload, token)
        elif event == "issues":
            if action == "opened":
                await handle_issue_opened(payload, token, blt_api_url)
            elif action == "labeled":
                await handle_issue_labeled(payload, token, blt_api_url)
        elif event == "pull_request":
            if action == "opened":
                await handle_pull_request_opened(payload, token)
            elif action == "closed":
                await handle_pull_request_closed(payload, token)
    except Exception as exc:
        console.error(f"[BLT] Webhook handler error: {exc}")
        return _json({"error": "Internal server error"}, 500)

    return _json({"ok": True})


# ---------------------------------------------------------------------------
# Landing page HTML
# ---------------------------------------------------------------------------


def _landing_html(app_slug: str) -> str:
    install_url = (
        f"https://github.com/apps/{app_slug}/installations/new"
        if app_slug
        else "https://github.com/apps/blt-github-app/installations/new"
    )
    year = time.gmtime().tm_year
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLT GitHub App</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #0d1117; color: #e6edf3; min-height: 100vh;
      display: flex; flex-direction: column; align-items: center;
    }}
    header {{
      width: 100%; background: #161b22; border-bottom: 1px solid #30363d;
      padding: 1rem 2rem; display: flex; align-items: center; gap: 1rem;
    }}
    header img {{ width: 40px; height: 40px; border-radius: 8px; }}
    header h1 {{ font-size: 1.25rem; font-weight: 700; color: #f0f6fc; flex: 1; }}
    .badge {{
      display: inline-flex; align-items: center; gap: 0.4rem;
      background: #238636; color: #fff; font-size: 0.75rem;
      font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 20px;
    }}
    .badge::before {{ content: "●"; font-size: 0.6rem; }}
    main {{ max-width: 900px; width: 100%; padding: 3rem 1.5rem; flex: 1; }}
    .hero {{
      text-align: center; padding: 4rem 2rem;
      border: 1px solid #30363d; border-radius: 12px;
      background: #161b22; margin-bottom: 3rem;
    }}
    .hero h2 {{ font-size: 2.25rem; font-weight: 800; margin-bottom: 1rem; color: #f0f6fc; }}
    .hero p {{
      font-size: 1.1rem; color: #8b949e; max-width: 600px;
      margin: 0 auto 2rem; line-height: 1.6;
    }}
    .btn {{
      display: inline-flex; align-items: center; gap: 0.5rem;
      background: #238636; color: #fff; font-size: 1rem; font-weight: 600;
      padding: 0.75rem 1.75rem; border-radius: 8px; text-decoration: none;
      transition: background 0.2s;
    }}
    .btn:hover {{ background: #2ea043; }}
    .btn svg {{ width: 20px; height: 20px; fill: currentColor; }}
    h2.section-title {{
      font-size: 1.25rem; font-weight: 700; margin-bottom: 1.25rem; color: #f0f6fc;
    }}
    .features {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.25rem; margin-bottom: 3rem;
    }}
    .card {{
      background: #161b22; border: 1px solid #30363d;
      border-radius: 10px; padding: 1.5rem;
    }}
    .card h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; color: #f0f6fc; }}
    .card p {{ font-size: 0.875rem; color: #8b949e; line-height: 1.6; }}
    .card .icon {{ font-size: 1.75rem; margin-bottom: 0.75rem; }}
    .card code {{
      background: #0d1117; padding: 0.1em 0.35em; border-radius: 4px;
      font-size: 0.85em;
    }}
    .status-section {{
      background: #161b22; border: 1px solid #30363d;
      border-radius: 10px; padding: 1.5rem; margin-bottom: 3rem;
    }}
    .status-row {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.6rem 0; border-bottom: 1px solid #30363d; font-size: 0.9rem;
    }}
    .status-row:last-child {{ border-bottom: none; }}
    .status-ok {{ color: #3fb950; font-weight: 600; }}
    .steps {{ counter-reset: step; margin-bottom: 3rem; }}
    .step {{
      background: #161b22; border: 1px solid #30363d; border-radius: 10px;
      padding: 1.25rem 1.5rem 1.25rem 4rem; margin-bottom: 1rem;
      position: relative; counter-increment: step;
    }}
    .step::before {{
      content: counter(step);
      position: absolute; left: 1.25rem; top: 1.25rem;
      width: 1.75rem; height: 1.75rem; background: #388bfd;
      color: #fff; font-weight: 700; font-size: 0.85rem;
      border-radius: 50%; display: flex; align-items: center; justify-content: center;
    }}
    .step h3 {{ font-size: 0.95rem; font-weight: 600; color: #f0f6fc; margin-bottom: 0.3rem; }}
    .step p {{ font-size: 0.875rem; color: #8b949e; line-height: 1.6; }}
    footer {{
      width: 100%; background: #161b22; border-top: 1px solid #30363d;
      padding: 1.5rem 2rem; text-align: center; font-size: 0.85rem; color: #8b949e;
    }}
    footer a {{ color: #388bfd; text-decoration: none; }}
    footer a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <header>
    <img
      src="https://avatars.githubusercontent.com/u/47849434?s=40"
      alt="OWASP BLT logo"
    />
    <h1>BLT GitHub App</h1>
    <span class="badge">Operational</span>
  </header>

  <main>
    <!-- Hero -->
    <section class="hero">
      <h2>Supercharge your GitHub org&nbsp;with&nbsp;BLT</h2>
      <p>
        Automate issue assignment, bug reporting to OWASP&nbsp;BLT, and
        contributor onboarding — powered by a lightweight Python Cloudflare Worker.
      </p>
      <a href="{install_url}" class="btn">
        <svg viewBox="0 0 16 16">
          <path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 0 0 5.47 7.59c.4.07.55-.17.55-.38
            0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
            -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
            .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15
            -.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.65 7.65 0 0 1 2-.27
            c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12
            .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48
            0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8
            c0-4.42-3.58-8-8-8z"/>
        </svg>
        Add to GitHub Organization
      </a>
    </section>

    <!-- Features -->
    <section>
      <h2 class="section-title">Features</h2>
      <div class="features">
        <div class="card">
          <div class="icon">📋</div>
          <h3>/assign &amp; /unassign</h3>
          <p>
            Comment <code>/assign</code> on any issue to claim it with a
            24-hour deadline. Release with <code>/unassign</code>.
          </p>
        </div>
        <div class="card">
          <div class="icon">🐛</div>
          <h3>Auto Bug Reporting</h3>
          <p>
            Issues labeled <code>bug</code>, <code>vulnerability</code>, or
            <code>security</code> are instantly reported to the OWASP BLT
            platform.
          </p>
        </div>
        <div class="card">
          <div class="icon">👋</div>
          <h3>Welcome Messages</h3>
          <p>
            New issues and pull requests receive friendly onboarding messages
            with contribution guidelines.
          </p>
        </div>
        <div class="card">
          <div class="icon">🎉</div>
          <h3>Merge Congratulations</h3>
          <p>
            Merged PRs trigger a celebratory acknowledgement for the
            contributor.
          </p>
        </div>
      </div>
    </section>

    <!-- Status -->
    <section class="status-section">
      <h2 class="section-title" style="margin-bottom:0.75rem;">System Status</h2>
      <div class="status-row">
        <span>Worker</span>
        <span class="status-ok">✓ Operational</span>
      </div>
      <div class="status-row">
        <span>GitHub Webhooks</span>
        <span class="status-ok">✓ Listening</span>
      </div>
      <div class="status-row">
        <span>BLT API</span>
        <span class="status-ok">✓ Connected</span>
      </div>
      <div class="status-row">
        <span>Webhook endpoint</span>
        <code style="font-size:0.8rem;color:#8b949e;">/api/github/webhooks</code>
      </div>
      <div class="status-row">
        <span>Health endpoint</span>
        <code style="font-size:0.8rem;color:#8b949e;">/health</code>
      </div>
    </section>

    <!-- How to add -->
    <section>
      <h2 class="section-title">How to Add to Your Organization</h2>
      <div class="steps">
        <div class="step">
          <h3>Click "Add to GitHub Organization" above</h3>
          <p>This starts the GitHub App installation flow.</p>
        </div>
        <div class="step">
          <h3>Choose your organization or account</h3>
          <p>
            Select the GitHub organization or personal account where you want
            to install BLT.
          </p>
        </div>
        <div class="step">
          <h3>Grant repository access</h3>
          <p>
            Choose which repositories the app should monitor — all repos or a
            specific selection.
          </p>
        </div>
        <div class="step">
          <h3>You're done!</h3>
          <p>
            BLT will immediately start responding to issues and pull requests
            in the selected repositories.
          </p>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <p>
      Built with ❤️ by
      <a
        href="https://owasp.org/www-project-bug-logging-tool/"
        target="_blank"
        rel="noopener"
      >OWASP BLT</a>
      &nbsp;·&nbsp;
      <a
        href="https://github.com/OWASP-BLT/BLT-GitHub-App"
        target="_blank"
        rel="noopener"
      >Source on GitHub</a>
      &nbsp;·&nbsp;
      <a href="https://owaspblt.org" target="_blank" rel="noopener">owaspblt.org</a>
      &nbsp;·&nbsp; © {year} OWASP BLT — AGPL-3.0
    </p>
  </footer>
</body>
</html>"""


_CALLBACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>BLT GitHub App — Installed!</title>
  <style>
    body {{
      font-family: system-ui, sans-serif; background: #0d1117; color: #e6edf3;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; margin: 0;
    }}
    .box {{
      text-align: center; padding: 3rem; background: #161b22;
      border: 1px solid #30363d; border-radius: 12px; max-width: 480px;
    }}
    h1 {{ color: #3fb950; font-size: 2rem; margin-bottom: 1rem; }}
    p {{ color: #8b949e; margin-bottom: 1.5rem; line-height: 1.6; }}
    a {{ color: #388bfd; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>🎉 Installation complete!</h1>
    <p>
      BLT GitHub App has been successfully installed on your organization.<br />
      Issues and pull requests will now be handled automatically.
    </p>
    <p><a href="https://owaspblt.org">Visit OWASP BLT →</a></p>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _json(data, status: int = 200) -> Response:
    return Response.new(
        json.dumps(data),
        status=status,
        headers=Headers.new({
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        }.items()),
    )


def _html(html: str, status: int = 200) -> Response:
    return Response.new(
        html,
        status=status,
        headers=Headers.new({"Content-Type": "text/html; charset=utf-8"}.items()),
    )


# ---------------------------------------------------------------------------
# Main entry point — called by the Cloudflare runtime
# ---------------------------------------------------------------------------


async def on_fetch(request, env) -> Response:
    method = request.method
    path = urlparse(str(request.url)).path.rstrip("/") or "/"

    if method == "GET" and path == "/":
        app_slug = getattr(env, "GITHUB_APP_SLUG", "")
        return _html(_landing_html(app_slug))

    if method == "GET" and path == "/health":
        return _json({"status": "ok", "service": "BLT GitHub App"})

    if method == "POST" and path == "/api/github/webhooks":
        return await handle_webhook(request, env)

    # GitHub redirects here after a successful installation
    if method == "GET" and path == "/callback":
        return _html(_CALLBACK_HTML)

    return _json({"error": "Not found"}, 404)
