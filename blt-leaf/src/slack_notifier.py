"""Slack error notification client for BLT-Leaf.

Sends error payloads to a configured Slack incoming webhook URL.
Uses js.fetch (available in Cloudflare Workers) to make the HTTP request.
"""

import json
import traceback
from js import fetch, Object
from pyodide.ffi import to_js


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
        return

    lines = [f"*{error_type}*: {error_message}"]

    if context:
        ctx_lines = [f"• *{k}*: {v}" for k, v in context.items()]
        lines.append("\n".join(ctx_lines))

    if stack_trace:
        # Truncate very long stack traces to avoid hitting Slack's message size limit
        truncated = stack_trace[:2000]
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
    except Exception as err:
        # Never let Slack notification errors bubble up and mask the original error
        print(f'Slack: failed to send error notification: {err}')


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
