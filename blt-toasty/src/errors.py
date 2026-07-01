"""
Custom exception classes for Toasty Cloudflare Worker.

These exceptions handle error states within the application,
particularly regarding the triage event state machine and security validations.
"""


class StateTransitionError(Exception):
    """
    Raised when an invalid state transition is attempted, or when a concurrent
    modification is detected during a state update.
    """

    pass


class RedactionFailedError(Exception):
    """
    Raised when redaction fails or does not meet required confidence thresholds.

    Attributes:
        confidence_score (float): The confidence score that caused the failure.
        entity_type (str): The type of entity that failed redaction.
    """

    def __init__(self, message: str, confidence_score: float, entity_type: str):
        super().__init__(message)
        self.confidence_score = confidence_score
        self.entity_type = entity_type


class HMACValidationError(Exception):
    """
    Raised when a webhook signature fails HMAC validation.
    """

    pass


class ReplayAttackError(Exception):
    """
    Raised when a webhook delivery ID has already been processed recently.

    Attributes:
        delivery_id (str): The duplicate delivery ID.
    """

    def __init__(self, message: str, delivery_id: str):
        super().__init__(message)
        self.delivery_id = delivery_id


class QuarantinedEventError(Exception):
    """
    Raised when attempting to process an event that has been quarantined.

    Attributes:
        event_id (str): The ID of the quarantined event.
    """

    def __init__(self, message: str, event_id: str):
        super().__init__(message)
        self.event_id = event_id
