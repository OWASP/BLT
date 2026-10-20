"""Slack error notification client for BLT-Leaf.

Sends error payloads to a configured Slack incoming webhook URL.
Uses js.fetch (available in Cloudflare Workers) to make the HTTP request.
"""

import json
import traceback
from js import fetch, Object
from pyodide.ffi import to_js


MAX_CONTEXT_FIELDS = 15


def slack_escape(value, limit):
    """Text for a Slack mrkdwn message, capped at `limit` characters.

    The client-error endpoint passes visitor-supplied text here. Escaping &, < and > (Slack's own
    rule) keeps `<https://evil|click>` links, `<!channel>`/`<!here>` and `<@U…>` mentions inert.
    """
    text = str(value if value is not None else "")[:limit]
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def notify_slack_error(webhook_url, error_type, error_message, context=None, stack_trace=None):
    """Send an error notification to a Slack incoming webhook.

    Args:
        webhook_url: Slack incoming webhook URL (from SLACK_ERROR_WEBHOOK env var).
        error_type: Short error type label, e.g. 'RuntimeError' or 'FrontendError'.
        error_message: Human-readable error message.
        context: Optional dict of additional key/value pairs (e.g. path, method).
        stack_trace: Optional stack trace string.
    """
    if not webhook_url:
        return False

    lines = [f"*{slack_escape(error_type, 100)}*: {slack_escape(error_message, 500)}"]

    if context:
        ctx_lines = [
            f"• *{slack_escape(k, 40)}*: {slack_escape(v, 200)}"
            for k, v in list(context.items())[:MAX_CONTEXT_FIELDS]
        ]
        lines.append("\n".join(ctx_lines))

    if stack_trace:
        # Truncate very long stack traces to avoid hitting Slack's message size limit
        stack_trace = str(stack_trace)
        # Backticks would close the code block early.
        truncated = slack_escape(stack_trace[:2000], 2000).replace("`", "'")
        if len(stack_trace) > 2000:
            truncated += "\n…(truncated)"
        lines.append(f"```{truncated}```")

    payload = {"text": "\n".join(lines)}

    try:
        options = to_js({
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(payload),
        }, dict_converter=Object.fromEntries)
        response = await fetch(webhook_url, options)
        if not response.ok:
            print(f'Slack: webhook returned HTTP {response.status}')
            return False
        return True
    except Exception as err:
        print(f'Slack: failed to send error notification: {err}')
        return False     


async def notify_slack_exception(webhook_url, exc, context=None):
    """Convenience wrapper to notify Slack about a Python exception.

    Args:
        webhook_url: Slack incoming webhook URL.
        exc: The exception instance.
        context: Optional dict of additional context.
    """
    stack_trace = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    await notify_slack_error(
        webhook_url,
        error_type=type(exc).__name__,
        error_message=str(exc),
        context=context,
        stack_trace=stack_trace,
    )
