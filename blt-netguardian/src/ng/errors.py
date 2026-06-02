"""Stable ingest error codes for ztr-finding-1."""

from enum import Enum


class IngestErrorCode(str, Enum):
    INVALID_ENVELOPE = "invalid_envelope"
    INVALID_PAYLOAD_MODE = "invalid_payload_mode"
    DIGEST_MISMATCH = "digest_mismatch"
    CLOCK_SKEW = "clock_skew"
    BAD_SIGNATURE = "bad_signature"
    UNKNOWN_KID = "unknown_kid"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    RATE_LIMITED = "rate_limited"


HTTP_STATUS = {
    IngestErrorCode.INVALID_ENVELOPE: 400,
    IngestErrorCode.INVALID_PAYLOAD_MODE: 400,
    IngestErrorCode.DIGEST_MISMATCH: 400,
    IngestErrorCode.CLOCK_SKEW: 400,
    IngestErrorCode.BAD_SIGNATURE: 401,
    IngestErrorCode.UNKNOWN_KID: 401,
    IngestErrorCode.PAYLOAD_TOO_LARGE: 413,
    IngestErrorCode.RATE_LIMITED: 429,
}


class IngestError(Exception):
    def __init__(self, code: IngestErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)

    @property
    def http_status(self) -> int:
        return HTTP_STATUS[self.code]

    def to_response_body(self) -> dict:
        return {"error": self.code.value, "message": self.message}
