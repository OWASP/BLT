"""
Lightweight Sentry error reporting for Cloudflare Python Workers.

This module provides minimal Sentry integration without heavy dependencies,
suitable for the Pyodide runtime.
"""

import json
import sys
import traceback
from datetime import datetime, timezone


class SentryClient:
    """Lightweight Sentry client for error reporting."""

    def __init__(self, dsn=None):
        """
        Initialize Sentry client.

        Args:
            dsn: Sentry DSN URL (e.g., https://key@sentry.io/project)
        """
        self.dsn = dsn
        self.enabled = bool(dsn)

        if self.dsn:
            self._parse_dsn()

    def _parse_dsn(self):
        """Parse Sentry DSN to extract configuration."""
        try:
            # Format: https://key@sentry.io/project_id
            # or https://key:secret@sentry.io/project_id
            parts = self.dsn.replace("https://", "").replace("http://", "").split("@")
            if len(parts) != 2:
                self.enabled = False
                return

            auth_part = parts[0]
            host_part = parts[1]

            # Parse auth
            if ":" in auth_part:
                self.key, self.secret = auth_part.split(":", 1)
            else:
                self.key = auth_part
                self.secret = ""

            # Parse host and project
            host_parts = host_part.split("/")
            self.host = host_parts[0]
            self.project_id = host_parts[1] if len(host_parts) > 1 else ""

            # Construct API endpoint
            self.api_url = f"https://{self.host}/api/{self.project_id}/store/"
        except Exception:
            self.enabled = False

    async def capture_exception(self, exc=None, level="error", extra=None):
        """
        Capture and report an exception to Sentry.

        Args:
            exc: Exception object (uses sys.exc_info() if None)
            level: Error level (error, warning, info)
            extra: Additional context data
        """
        if not self.enabled:
            return

        try:
            if exc is None:
                exc_info = sys.exc_info()
                if exc_info[0] is None:
                    return
                exc = exc_info[1]
            else:
                exc_info = (type(exc), exc, exc.__traceback__)

            # Build Sentry payload
            payload = self._build_payload(exc, exc_info, level, extra)

            # Send to Sentry without blocking request execution.
            self._send_payload(payload)
        except Exception:
            # Silently fail - don't break the worker
            pass

    def capture_exception_nowait(self, exc=None, level="error", extra=None):
        """Capture exception without awaiting, safe for worker hot paths."""
        if not self.enabled:
            return

        try:
            if exc is None:
                exc_info = sys.exc_info()
                if exc_info[0] is None:
                    return
                exc = exc_info[1]
            else:
                exc_info = (type(exc), exc, exc.__traceback__)

            payload = self._build_payload(exc, exc_info, level, extra)
            self._send_payload(payload)
        except Exception:
            pass

    def _build_payload(self, exc, exc_info, level, extra):
        """Build Sentry event payload."""
        exc_type, exc_value, exc_traceback = exc_info

        # Format exception traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = "".join(tb_lines)

        # Build frames for stack trace
        frames = []
        if exc_traceback:
            tb = exc_traceback
            while tb:
                frame = tb.tb_frame
                frames.append(
                    {
                        "filename": frame.f_code.co_filename,
                        "function": frame.f_code.co_name,
                        "lineno": tb.tb_lineno,
                        "context_line": frame.f_code.co_name,
                    }
                )
                tb = tb.tb_next

        payload = {
            "event_id": self._generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "platform": "python",
            "sdk": {
                "name": "blt-lettuce-worker",
                "version": "1.0.0",
            },
            "exception": {
                "values": [
                    {
                        "type": exc_type.__name__ if exc_type else "Unknown",
                        "value": str(exc_value) if exc_value else "",
                        "stacktrace": {
                            "frames": frames,
                        },
                    }
                ]
            },
            "message": {
                "message": str(exc_value) if exc_value else tb_text,
            },
            "extra": extra or {},
        }

        return payload

    @staticmethod
    def _generate_event_id():
        """Generate a Sentry event ID."""
        import uuid

        return str(uuid.uuid4()).replace("-", "")

    def _send_payload(self, payload):
        """Send payload to Sentry API."""
        try:
            from js import Headers, fetch
        except ImportError:
            return

        try:
            headers = Headers.new()
            headers.set("Content-Type", "application/json")
            headers.set(
                "X-Sentry-Auth",
                f"Sentry sentry_key={self.key}, sentry_version=7",
            )
            # Fire-and-forget network send. Avoid awaiting here because
            # nested awaits in worker exception paths can deadlock Pyodide tasks.
            fetch(
                self.api_url,
                {
                    "method": "POST",
                    "headers": headers,
                    "body": json.dumps(payload),
                },
            )
        except Exception:
            pass

    async def capture_message(self, message, level="info", extra=None):
        """
        Capture a message to Sentry.

        Args:
            message: Message string
            level: Message level
            extra: Additional context
        """
        if not self.enabled:
            return

        try:
            payload = {
                "event_id": self._generate_event_id(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "platform": "python",
                "sdk": {
                    "name": "blt-lettuce-worker",
                    "version": "1.0.0",
                },
                "message": {
                    "message": message,
                },
                "extra": extra or {},
            }

            self._send_payload(payload)
        except Exception:
            pass


# Global client instance
_sentry_client = None


def init_sentry(dsn=None):
    """Initialize global Sentry client."""
    global _sentry_client
    _sentry_client = SentryClient(dsn)
    return _sentry_client


def get_sentry():
    """Get global Sentry client instance."""
    global _sentry_client
    if _sentry_client is None:
        _sentry_client = SentryClient()
    return _sentry_client
