"""Lightweight PostHog client for error tracking in Cloudflare Workers Python.

Uses the js.fetch API (available in Cloudflare Workers) to send events to
PostHog, since the standard posthog SDK relies on the `requests` library and
threading which are not available in the Workers runtime.
"""

import asyncio
import json
import sys
import traceback
from js import fetch, Object
from pyodide.ffi import to_js


class PostHog:
    """PostHog error tracking client for Cloudflare Workers."""

    def __init__(self, project_api_key, host='https://us.i.posthog.com',
                 enable_exception_autocapture=False):
        self.project_api_key = project_api_key
        # Normalise host: strip trailing slash
        self.host = host.rstrip('/')
        self.enable_exception_autocapture = enable_exception_autocapture
        if enable_exception_autocapture:
            self._setup_exception_autocapture()

    def _setup_exception_autocapture(self):
        """Install sys.excepthook (and threading.excepthook when available).

        Automatically captures any unhandled exception and forwards it to
        PostHog as a ``$exception`` event, mirroring the behaviour of the
        official PostHog Python SDK's ``enable_exception_autocapture`` option.
        """
        original_excepthook = sys.excepthook

        def _excepthook(exc_type, exc_value, exc_tb):
            self._schedule_capture(exc_value)
            original_excepthook(exc_type, exc_value, exc_tb)

        sys.excepthook = _excepthook

        # threading.excepthook is not available in all environments (e.g.
        # Cloudflare Workers / Pyodide), so guard with a try/except.
        try:
            import threading
            original_threading_excepthook = threading.excepthook

            def _threading_excepthook(args):
                self._schedule_capture(args.exc_value)
                original_threading_excepthook(args)

            threading.excepthook = _threading_excepthook
        except (ImportError, AttributeError):
            pass  # threading not available in this environment

    def _schedule_capture(self, exc_value):
        """Schedule an async capture_exception call from a synchronous hook."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.capture_exception(exc_value))
            else:
                loop.run_until_complete(self.capture_exception(exc_value))
        except Exception as schedule_err:
            print(f'PostHog: failed to schedule exception capture: {schedule_err}')

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
