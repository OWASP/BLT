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
    from pyodide.ffi import to_js  # noqa: PLC0415 — runtime import

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
        to_js({"name": "RSASSA-PKCS1-v1_5", "hash": "SHA-256"}),
        False,
        to_js(["sign"]),
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
# Landing page HTML — embedded at build time to avoid filesystem access in
# the Cloudflare Workers Python runtime (where open() cannot reach public/).
# ---------------------------------------------------------------------------

_INDEX_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLT GitHub App</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link
    rel="stylesheet"
    href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
    crossorigin="anonymous"
    referrerpolicy="no-referrer"
  />
</head>
<body class="min-h-screen flex flex-col" style="background:#111827;color:#e5e7eb;">
  <!-- Header -->
  <header class="w-full px-6 py-3 flex items-center gap-3" style="background:#1F2937;border-bottom:1px solid #374151;">
    <img
      src="https://avatars.githubusercontent.com/u/47849434?s=40"
      alt="OWASP BLT logo"
      class="w-10 h-10 rounded-lg"
    />
    <h1 class="flex-1 text-lg font-bold text-white">BLT GitHub App</h1>
    <span role="status" aria-label="Service status: Operational" class="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full" style="background:rgba(74,222,128,0.1);color:#4ade80;border:1px solid rgba(74,222,128,0.25);">
      <i class="fa-solid fa-circle" style="font-size:0.45rem;" aria-hidden="true"></i>
      Operational
    </span>
  </header>

  <!-- Main -->
  <main class="flex-1 w-full max-w-4xl mx-auto px-4 py-12">

    <!-- Hero -->
    <section class="text-center py-16 px-8 rounded-xl mb-12" style="background:#1F2937;border:1px solid #374151;">
      <h2 class="text-4xl font-extrabold text-white mb-4">
        Supercharge your GitHub&nbsp;org&nbsp;with&nbsp;BLT
      </h2>
      <p class="text-lg max-w-xl mx-auto mb-8 leading-relaxed" style="color:#9ca3af;">
        Automate issue assignment, bug reporting to OWASP&nbsp;BLT, and
        contributor onboarding — powered by a lightweight Python Cloudflare Worker.
      </p>
      <div class="flex flex-wrap justify-center gap-3">
        <a
          href="{{INSTALL_URL}}"
          class="inline-flex items-center gap-2 text-white font-semibold text-base px-6 py-3 rounded-lg transition-colors"
          style="background:#E10101;"
          onmouseover="this.style.background='#b91c1c'" onmouseout="this.style.background='#E10101'"
        >
          <i class="fa-brands fa-github" aria-hidden="true"></i>
          Add to GitHub Organization
        </a>
        <a
          href="https://github.com/OWASP-BLT/BLT-GitHub-App"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-2 font-semibold text-base px-6 py-3 rounded-lg transition-colors"
          style="border:1px solid #E10101;color:#E10101;"
          onmouseover="this.style.background='#E10101';this.style.color='#fff'" onmouseout="this.style.background='transparent';this.style.color='#E10101'"
        >
          <i class="fa-solid fa-code" aria-hidden="true"></i>
          View Source
        </a>
      </div>
    </section>

    <!-- Features -->
    <section class="mb-12">
      <h2 class="text-xl font-bold text-white mb-5">Features</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">

        <div class="rounded-xl p-6" style="background:#1F2937;border:1px solid #374151;">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center mb-4" style="background:rgba(225,1,1,0.1);">
            <i class="fa-solid fa-list-check text-lg" style="color:#E10101;" aria-hidden="true"></i>
          </div>
          <h3 class="text-white font-semibold mb-2">/assign &amp; /unassign</h3>
          <p class="text-sm leading-relaxed" style="color:#9ca3af;">
            Comment <code class="rounded text-xs px-1.5 py-0.5" style="background:#111827;">/assign</code> on any
            issue to claim it with a 24-hour deadline. Release with
            <code class="rounded text-xs px-1.5 py-0.5" style="background:#111827;">/unassign</code>.
          </p>
        </div>

        <div class="rounded-xl p-6" style="background:#1F2937;border:1px solid #374151;">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center mb-4" style="background:rgba(225,1,1,0.1);">
            <i class="fa-solid fa-bug text-lg" style="color:#E10101;" aria-hidden="true"></i>
          </div>
          <h3 class="text-white font-semibold mb-2">Auto Bug Reporting</h3>
          <p class="text-sm leading-relaxed" style="color:#9ca3af;">
            Issues labeled <code class="rounded text-xs px-1.5 py-0.5" style="background:#111827;">bug</code>,
            <code class="rounded text-xs px-1.5 py-0.5" style="background:#111827;">vulnerability</code>, or
            <code class="rounded text-xs px-1.5 py-0.5" style="background:#111827;">security</code> are instantly
            reported to the OWASP BLT platform.
          </p>
        </div>

        <div class="rounded-xl p-6" style="background:#1F2937;border:1px solid #374151;">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center mb-4" style="background:rgba(225,1,1,0.1);">
            <i class="fa-solid fa-comments text-lg" style="color:#E10101;" aria-hidden="true"></i>
          </div>
          <h3 class="text-white font-semibold mb-2">Welcome Messages</h3>
          <p class="text-sm leading-relaxed" style="color:#9ca3af;">
            New issues and pull requests receive friendly onboarding messages
            with contribution guidelines.
          </p>
        </div>

        <div class="rounded-xl p-6" style="background:#1F2937;border:1px solid #374151;">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center mb-4" style="background:rgba(225,1,1,0.1);">
            <i class="fa-solid fa-trophy text-lg" style="color:#E10101;" aria-hidden="true"></i>
          </div>
          <h3 class="text-white font-semibold mb-2">Merge Congratulations</h3>
          <p class="text-sm leading-relaxed" style="color:#9ca3af;">
            Merged PRs trigger a celebratory acknowledgement for the
            contributor.
          </p>
        </div>

      </div>
    </section>

    <!-- System Status -->
    <section class="rounded-xl p-6 mb-12" style="background:#1F2937;border:1px solid #374151;">
      <h2 class="text-xl font-bold text-white mb-4">System Status</h2>
      <div style="border-top:1px solid #374151;">

        <div class="flex justify-between items-center py-3 text-sm" style="border-bottom:1px solid #374151;">
          <span style="color:#d1d5db;">Worker</span>
          <span class="font-semibold flex items-center gap-1.5" style="color:#4ade80;">
            <i class="fa-solid fa-circle-check" aria-hidden="true"></i> Operational
          </span>
        </div>

        <div class="flex justify-between items-center py-3 text-sm" style="border-bottom:1px solid #374151;">
          <span style="color:#d1d5db;">GitHub Webhooks</span>
          <span class="font-semibold flex items-center gap-1.5" style="color:#4ade80;">
            <i class="fa-solid fa-circle-check" aria-hidden="true"></i> Listening
          </span>
        </div>

        <div class="flex justify-between items-center py-3 text-sm" style="border-bottom:1px solid #374151;">
          <span style="color:#d1d5db;">BLT API</span>
          <span class="font-semibold flex items-center gap-1.5" style="color:#4ade80;">
            <i class="fa-solid fa-circle-check" aria-hidden="true"></i> Connected
          </span>
        </div>

        <div class="flex justify-between items-center py-3 text-sm" style="border-bottom:1px solid #374151;">
          <span style="color:#d1d5db;">Webhook endpoint</span>
          <code class="rounded text-xs px-2 py-0.5" style="background:#111827;color:#9ca3af;">/api/github/webhooks</code>
        </div>

        <div class="flex justify-between items-center py-3 text-sm">
          <span style="color:#d1d5db;">Health endpoint</span>
          <code class="rounded text-xs px-2 py-0.5" style="background:#111827;color:#9ca3af;">/health</code>
        </div>

{{SECRET_VARS_STATUS}}
      </div>
    </section>

    <!-- How to Add -->
    <section class="mb-12">
      <h2 class="text-xl font-bold text-white mb-5">How to Add to Your Organization</h2>
      <ol class="space-y-3">

        <li class="relative rounded-xl px-6 py-4 pl-16" style="background:#1F2937;border:1px solid #374151;">
          <span class="absolute left-5 top-4 w-7 h-7 text-white text-xs font-bold rounded-full flex items-center justify-center" style="background:#E10101;" aria-hidden="true">1</span>
          <h3 class="text-white font-semibold text-sm mb-1">Click &#34;Add to GitHub Organization&#34; above</h3>
          <p class="text-sm" style="color:#9ca3af;">This starts the GitHub App installation flow.</p>
        </li>

        <li class="relative rounded-xl px-6 py-4 pl-16" style="background:#1F2937;border:1px solid #374151;">
          <span class="absolute left-5 top-4 w-7 h-7 text-white text-xs font-bold rounded-full flex items-center justify-center" style="background:#E10101;" aria-hidden="true">2</span>
          <h3 class="text-white font-semibold text-sm mb-1">Choose your organization or account</h3>
          <p class="text-sm" style="color:#9ca3af;">
            Select the GitHub organization or personal account where you want to install BLT.
          </p>
        </li>

        <li class="relative rounded-xl px-6 py-4 pl-16" style="background:#1F2937;border:1px solid #374151;">
          <span class="absolute left-5 top-4 w-7 h-7 text-white text-xs font-bold rounded-full flex items-center justify-center" style="background:#E10101;" aria-hidden="true">3</span>
          <h3 class="text-white font-semibold text-sm mb-1">Grant repository access</h3>
          <p class="text-sm" style="color:#9ca3af;">
            Choose which repositories the app should monitor — all repos or a specific selection.
          </p>
        </li>

        <li class="relative rounded-xl px-6 py-4 pl-16" style="background:#1F2937;border:1px solid #374151;">
          <span class="absolute left-5 top-4 w-7 h-7 text-white text-xs font-bold rounded-full flex items-center justify-center" style="background:#E10101;" aria-hidden="true">4</span>
          <h3 class="text-white font-semibold text-sm mb-1">You&#39;re done!</h3>
          <p class="text-sm" style="color:#9ca3af;">
            BLT will immediately start responding to issues and pull requests in the selected repositories.
          </p>
        </li>

      </ol>
    </section>

  </main>

  <!-- Footer -->
  <footer class="w-full px-6 py-5 text-center text-sm" style="background:#1F2937;border-top:1px solid #374151;color:#9ca3af;">
    <p>
      Built with <i class="fa-solid fa-heart" style="color:#E10101;" aria-hidden="true"></i> by
      <a href="https://owasp.org/www-project-bug-logging-tool/" target="_blank" rel="noopener"
         style="color:#E10101;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">OWASP BLT</a>
      &nbsp;·&nbsp;
      <a href="https://github.com/OWASP-BLT/BLT-GitHub-App" target="_blank" rel="noopener"
         style="color:#E10101;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">Source on GitHub</a>
      &nbsp;·&nbsp;
      <a href="https://owaspblt.org" target="_blank" rel="noopener"
         style="color:#E10101;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">owaspblt.org</a>
      &nbsp;·&nbsp; © {{YEAR}} OWASP BLT — AGPL-3.0
    </p>
  </footer>
</body>
</html>
"""

_CALLBACK_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLT GitHub App — Installed!</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link
    rel="stylesheet"
    href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
    crossorigin="anonymous"
    referrerpolicy="no-referrer"
  />
</head>
<body class="min-h-screen flex items-center justify-center" style="background:#111827;color:#e5e7eb;">
  <div class="text-center rounded-xl p-12 max-w-md w-full mx-4" style="background:#1F2937;border:1px solid #374151;">
    <div class="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6" style="background:rgba(225,1,1,0.1);">
      <i class="fa-solid fa-circle-check text-3xl" style="color:#E10101;" aria-hidden="true"></i>
    </div>
    <h1 class="text-2xl font-bold text-white mb-4">Installation complete!</h1>
    <p class="leading-relaxed mb-6" style="color:#9ca3af;">
      BLT GitHub App has been successfully installed on your organization.<br />
      Issues and pull requests will now be handled automatically.
    </p>
    <a
      href="https://owaspblt.org"
      target="_blank"
      rel="noopener"
      style="color:#E10101;"
      onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'"
    >
      Visit OWASP BLT <i class="fa-solid fa-arrow-right text-xs" aria-hidden="true"></i>
    </a>
  </div>
</body>
</html>
"""


def _secret_vars_status_html(env) -> str:
    """Generate HTML rows showing whether each secret/config variable is set."""
    _SET_BADGE = (
        '<span class="font-semibold flex items-center gap-1.5" style="color:#4ade80;">'
        '<i class="fa-solid fa-circle-check" aria-hidden="true"></i> Set'
        "</span>"
    )
    _MISSING_BADGE = (
        '<span class="font-semibold flex items-center gap-1.5" style="color:#f87171;">'
        '<i class="fa-solid fa-circle-xmark" aria-hidden="true"></i> Not set'
        "</span>"
    )
    _OPTIONAL_BADGE = (
        '<span class="font-semibold flex items-center gap-1.5" style="color:#9ca3af;">'
        '<i class="fa-solid fa-circle-minus" aria-hidden="true"></i> Not configured'
        "</span>"
    )

    required_vars = ["APP_ID", "PRIVATE_KEY", "WEBHOOK_SECRET"]
    optional_vars = ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"]

    rows = [
        '        <div style="border-top:1px solid #374151;margin-top:1rem;padding-top:0.5rem;">',
        '          <p class="text-xs font-semibold uppercase tracking-wider mb-1" style="color:#6b7280;">Secret Variables</p>',
        "        </div>",
    ]
    for name in required_vars:
        is_set = bool(getattr(env, name, ""))
        badge = _SET_BADGE if is_set else _MISSING_BADGE
        rows.append(
            f'        <div class="flex justify-between items-center py-3 text-sm" style="border-bottom:1px solid #374151;">'
            f'<span style="color:#d1d5db;"><code style="font-size:0.75rem;">{name}</code></span>'
            f"{badge}</div>"
        )
    for name in optional_vars:
        is_set = bool(getattr(env, name, ""))
        badge = _SET_BADGE if is_set else _OPTIONAL_BADGE
        rows.append(
            f'        <div class="flex justify-between items-center py-3 text-sm" style="border-bottom:1px solid #374151;">'
            f'<span style="color:#d1d5db;"><code style="font-size:0.75rem;">{name}</code>'
            f' <span style="color:#6b7280;font-size:0.7rem;">(optional)</span></span>'
            f"{badge}</div>"
        )
    return "\n".join(rows)


def _landing_html(app_slug: str, env=None) -> str:
    install_url = (
        f"https://github.com/apps/{app_slug}/installations/new"
        if app_slug
        else "https://github.com/apps/blt-github-app/installations/new"
    )
    year = time.gmtime().tm_year
    secret_vars_html = _secret_vars_status_html(env) if env is not None else ""
    return (
        _INDEX_HTML_TEMPLATE
        .replace("{{INSTALL_URL}}", install_url)
        .replace("{{YEAR}}", str(year))
        .replace("{{SECRET_VARS_STATUS}}", secret_vars_html)
    )


def _callback_html() -> str:
    return _CALLBACK_HTML


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
        return _html(_landing_html(app_slug, env))

    if method == "GET" and path == "/health":
        return _json({"status": "ok", "service": "BLT GitHub App"})

    if method == "POST" and path == "/api/github/webhooks":
        return await handle_webhook(request, env)

    # GitHub redirects here after a successful installation
    if method == "GET" and path == "/callback":
        return _html(_callback_html())

    return _json({"error": "Not found"}, 404)
