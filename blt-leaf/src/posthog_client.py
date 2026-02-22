"""Lightweight PostHog client for error tracking in Cloudflare Workers Python.

Uses the js.fetch API (available in Cloudflare Workers) to send events to
PostHog, since the standard posthog SDK relies on the `requests` library and
threading which are not available in the Workers runtime.
"""

import json
import traceback
from js import fetch, Object
from pyodide.ffi import to_js


class PostHog:
    """PostHog error tracking client for Cloudflare Workers."""

    def __init__(self, project_api_key, host='https://us.i.posthog.com'):
        self.project_api_key = project_api_key
        # Normalise host: strip trailing slash
        self.host = host.rstrip('/')

    async def capture(self, distinct_id, event, properties=None):
        """Send a single event to PostHog.

        Args:
            distinct_id: Identifier for the actor (use a fixed server ID for
                         server-side error tracking).
            event: Event name, e.g. '$exception'.
            properties: Optional dict of event properties.
        """
        if not self.project_api_key:
            return

        payload = {
            'api_key': self.project_api_key,
            'event': event,
            'distinct_id': distinct_id,
            'properties': properties or {},
        }

        try:
            options = to_js({
                'method': 'POST',
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(payload),
            }, dict_converter=Object.fromEntries)
            response = await fetch(f'{self.host}/capture/', options)
            if not response.ok:
                print(f'PostHog: capture returned HTTP {response.status}')
        except Exception as capture_err:
            # Never let PostHog errors bubble up and mask the original error
            print(f'PostHog: failed to send event: {capture_err}')

    async def capture_exception(self, exc, context=None):
        """Capture an exception as a PostHog $exception event.

        Args:
            exc: The exception instance to report.
            context: Optional dict with additional context (e.g. path, method).
        """
        properties = {
            '$exception_type': type(exc).__name__,
            '$exception_message': str(exc),
            '$exception_stack_trace_raw': traceback.format_exc(),
        }
        if context:
            properties.update(context)

        await self.capture(
            distinct_id='blt-leaf-server',
            event='$exception',
            properties=properties,
        )
