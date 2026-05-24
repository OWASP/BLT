import json
import time
import queue
import threading
import logging
from typing import Any

logger = logging.getLogger(__name__)

class MCPResponseReader:
    """
    Manages a single background reader thread for a process stdout.
    Separates responses (have id) from notifications (no id).
    Create once per process, reuse across multiple read calls.
    """

    def __init__(self, process):
        self._responses: queue.Queue = queue.Queue()
        self._notifications: list[dict] = []
        self._lock = threading.Lock()
        self._stopped = False
        self._process = process
        self._reader_error: Exception | None = None

        self._thread = threading.Thread(
            target=self._read_loop,
            args=(process.stdout,),
            daemon=True
        )
        self._thread.start()

    def _read_loop(self, pipe):
        try:
            for line in pipe:
                if not line or self._stopped:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Malformed JSON line received: %r", line)
                    continue

                if "id" in msg:
                    self._responses.put(msg)
                else:
                    with self._lock:
                        self._notifications.append(msg)
        except Exception as e:
            self._reader_error = e
            logger.exception("Reader loop failed")

    def read_response(self, expected_id: Any, timeout: float = 35.0) -> dict:
        """
        Block until a response with expected_id arrives or timeout expires.
        Responses with other IDs are re-queued so other callers can get them.
        """
        deadline = time.monotonic() + timeout
        pending = []

        try:
            while time.monotonic() < deadline:
                if self._reader_error is not None:
                    raise RuntimeError("Stdout reader thread failed") from self._reader_error
                if (
                    self._process.poll() is not None
                    and self._responses.empty()
                    and not self._thread.is_alive()
                ):
                    raise RuntimeError(f"Process exited with code {self._process.returncode}")
                    
                remaining = deadline - time.monotonic()
                try:
                    response = self._responses.get(timeout=max(min(remaining, 0.1), 0))
                except queue.Empty:
                    continue

                if response.get("id") == expected_id:
                    return response
                else:
                    # Not ours — put aside and re-queue after
                    pending.append(response)
        finally:
            for r in pending:
                self._responses.put(r)

        raise TimeoutError(
            f"Timed out after {timeout}s waiting for "
            f"JSON-RPC response with id={expected_id!r}"
        )

    def get_notifications(self) -> list[dict]:
        """Returns a copy of all notifications received so far."""
        with self._lock:
            return list(self._notifications)

    def stop(self):
        self._stopped = True

# Helper to maintain compatibility with existing tests
_readers = {}

def read_jsonrpc_response(process, expected_id, timeout=35.0):
    if process not in _readers:
        _readers[process] = MCPResponseReader(process)
    return _readers[process].read_response(expected_id, timeout)
