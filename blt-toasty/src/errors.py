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


class LLMUnavailableError(Exception):
    """Raised when all configured LLM providers are unreachable.

    This exception is the terminal failure state for the LLM router.
    Both the primary provider (Cloudflare Workers AI) and the fallback
    provider (OpenAI) have failed, and no further retry is possible
    within the current request lifecycle.

    Attributes:
        providers_tried: List of provider names that were attempted.
        last_error: The error message from the last provider that failed.
    """

    def __init__(self, message: str, *, providers_tried: list[str] | None = None, last_error: str = ""):
        super().__init__(message)
        self.providers_tried = providers_tried or []
        self.last_error = last_error


class EmbeddingServiceError(Exception):
    """Raised when the FastEmbed sidecar is unreachable or returns an error.

    This exception is used by the embedding client when the sidecar
    service times out, returns a non-200 response, or produces
    embeddings with incorrect dimensions.

    Attributes:
        status_code: The HTTP status code from the sidecar (if available).
    """

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class GitLabAPIError(Exception):
    """Raised when a GitLab REST API call fails.

    Used by ``gitlab_linker`` when the GitLab API returns a non-success
    HTTP status code (e.g. 403 Forbidden, 404 Not Found, 429 Rate Limited).

    Attributes:
        status_code: The HTTP status code from GitLab.
    """

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AuditIncompleteError(Exception):
    """Raised when audit_completeness_check() determines that required audit fields are absent.

    This is the terminal failure state for MCP export gating.  The caller should
    surface HTTP 424 Failed Dependency to clients along with the ``missing_fields``
    list so operators can diagnose which pipeline stage did not complete.

    Attributes:
        event_id: The event whose audit is incomplete.
        missing_fields: Names of the audit records that are absent from D1
            (subset of ``["triage_summary", "triage_rationale", "redaction_audit"]``).
    """

    def __init__(self, message: str, *, event_id: str = "", missing_fields: list[str] | None = None):
        super().__init__(message)
        self.event_id = event_id
        self.missing_fields: list[str] = missing_fields or []


class ConversationError(Exception):
    """Raised when a conversation operation fails.

    Used by the ``ConversationDO`` Durable Object when a conversation
    turn cannot be appended, archived, or retrieved.

    Attributes:
        status_code: The HTTP status code to surface to the client.
    """

    def __init__(self, message: str = "Conversation operation failed", *, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code
