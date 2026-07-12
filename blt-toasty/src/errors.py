"""
Custom exception classes for the Toasty Cloudflare Worker.

These exceptions handle error states within the application,
particularly regarding the triage event state machine, security validations,
and PII redaction enforcement.
"""


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted.

    This is the primary guard exception used by ``assert_redacted_before_downstream``
    to block any downstream processing (summariser, embedder, MCP export) when
    the event has not yet passed the redaction gate.

    Attributes:
        event_id: The event that failed the transition check.
        current_status: The status that was found instead of the expected one.
        http_status: The recommended HTTP status code to surface (default 423 Locked).
    """

    def __init__(self, message: str, *, event_id: str = "", current_status: str = "", http_status: int = 423):
        super().__init__(message)
        self.event_id = event_id
        self.current_status = current_status
        self.http_status = http_status


class RedactionFailedError(Exception):
    """Raised when the redaction pipeline cannot guarantee PII-free output.

    Triggering this exception causes the event to be quarantined and the
    state machine to transition to ``redaction_failed``.

    Attributes:
        event_id: The event whose redaction failed.
        reason: A human-readable explanation of why redaction was rejected.
    """

    def __init__(self, message: str, *, event_id: str = "", reason: str = ""):
        super().__init__(message)
        self.event_id = event_id
        self.reason = reason


class QuarantinedEventError(Exception):
    """Raised when attempting to process an event that has been quarantined.

    Attributes:
        event_id: The ID of the quarantined event.
    """

    def __init__(self, message: str, *, event_id: str = ""):
        super().__init__(message)
        self.event_id = event_id


class HMACValidationError(Exception):
    """Raised when a webhook signature fails HMAC validation."""

    pass


class ReplayAttackError(Exception):
    """Raised when a webhook delivery ID has already been processed recently.

    Attributes:
        delivery_id: The duplicate delivery ID.
    """

    def __init__(self, message: str, *, delivery_id: str = ""):
        super().__init__(message)
        self.delivery_id = delivery_id
