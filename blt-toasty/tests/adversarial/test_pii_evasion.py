"""Adversarial tests for PII evasion.

Covers:
    1. Base64-encoded (KNOWN LIMITATION)
    2. Hex-encoded (KNOWN LIMITATION)
    3. Zero-width space insertion (ZWS)
    4. Zero-width non-joiner (ZWNJ)
    5. Zero-width joiner (ZWJ)
    6. Split across newline
    7. Image alt text
    8. Inline code
    9. Zero-width in IP octets
    10. Zero-width in tokens
    11. Homoglyph in keyword (KNOWN LIMITATION)
    12. BOM prefix evasion
    13. Base64 IP (KNOWN LIMITATION)
    14. Reversed string (KNOWN LIMITATION)
    15. URL encoding (KNOWN LIMITATION)

Validates that the native redaction engine and markdown preprocessor
correctly strip adversarial zero-width characters and find PII embedded
within markdown syntax, while documenting unhandled encoding vectors
as known limitations.
"""

from __future__ import annotations


from src.markdown_preprocessor import extract_plain_text
from src.native_recognizers import apply_native_redaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_entity_detected(text: str, expected_type: str) -> None:
    """Assert that applying redaction detects the expected entity type."""
    # We must preprocess if there's markdown, but for direct tests scan_text is often enough.
    # We will test apply_native_redaction which does not do markdown prep.
    # Wait, the full pipeline does both. Let's test the native engine directly here.
    _, matches = apply_native_redaction(text)
    types = [m["entity_type"] for m in matches]
    assert expected_type in types, f"Failed to detect {expected_type} in {repr(text)}"


def _assert_not_detected(text: str) -> None:
    """Assert that no PII is detected (used for documenting limitations)."""
    _, matches = apply_native_redaction(text)
    assert not matches, f"Expected no matches, but got: {matches}"


# ---------------------------------------------------------------------------
# Tests: Evasion vectors
# ---------------------------------------------------------------------------


class TestPIIEvasion:
    """Tests verifying PII evasion defenses."""

    # -----------------------------------------------------------------------
    # Detected Vectors (Hardened)
    # -----------------------------------------------------------------------

    def test_zero_width_space_email(self):
        """Attempt: Insert U+200B (ZWS) inside an email."""
        text = "Contact te\u200bst@ex\u200bample.c\u200bom immediately."
        _assert_entity_detected(text, "EMAIL_ADDRESS")

    def test_zero_width_non_joiner_email(self):
        """Attempt: Insert U+200C (ZWNJ) inside an email."""
        text = "Contact te\u200cst@exa\u200cmple.com immediately."
        _assert_entity_detected(text, "EMAIL_ADDRESS")

    def test_zero_width_joiner_email(self):
        """Attempt: Insert U+200D (ZWJ) inside an email."""
        text = "Contact te\u200dst@exa\u200dmple.com immediately."
        _assert_entity_detected(text, "EMAIL_ADDRESS")

    def test_zero_width_in_ip_octets(self):
        """Attempt: Insert ZWS into an IP address."""
        text = "Server IP is 192.\u200b168.\u200b1.\u200b1 for internal access."
        _assert_entity_detected(text, "IP_ADDRESS")

    def test_zero_width_in_github_token(self):
        """Attempt: Insert ZWS into a GitHub token."""
        # Must be at least 36 characters after ghp_
        text = "Auth using ghp_abc\u200bdef\u200bghi\u200bjklmnopqr\u200bstuvwxyz0123456789"
        _assert_entity_detected(text, "GITHUB_TOKEN")

    def test_bom_prefix_evasion(self):
        """Attempt: Prefix an email with U+FEFF (BOM)."""
        text = "Admin email: \ufeffadmin@example.com"
        _assert_entity_detected(text, "EMAIL_ADDRESS")

    def test_markdown_image_alt_text(self):
        """Attempt: Hide email in image alt text."""
        md = "![test@example.com](image.png)"
        plain = extract_plain_text(md)
        _assert_entity_detected(plain, "EMAIL_ADDRESS")

    def test_markdown_inline_code(self):
        """Attempt: Hide email in inline code."""
        md = "Email is `admin@secret.internal`."
        plain = extract_plain_text(md)
        _assert_entity_detected(plain, "EMAIL_ADDRESS")

    # -----------------------------------------------------------------------
    # Known Limitations (Undetected Vectors)
    # -----------------------------------------------------------------------

    def test_base64_encoded_email(self):
        """Attempt: Base64-encode an email. (KNOWN LIMITATION)"""
        # "test@example.com" -> dGVzdEBleGFtcGxlLmNvbQ==
        text = "Contact dGVzdEBleGFtcGxlLmNvbQ== for support."
        _assert_not_detected(text)

    def test_hex_encoded_ip(self):
        """Attempt: Hex-encode an IP address. (KNOWN LIMITATION)"""
        # 192.168.1.1 -> \x31\x39\x32\x2e\x31\x36\x38\x2e\x31\x2e\x31
        text = r"Ping \x31\x39\x32\x2e\x31\x36\x38\x2e\x31\x2e\x31"
        _assert_not_detected(text)

    def test_base64_encoded_ip(self):
        """Attempt: Base64-encode an IP address. (KNOWN LIMITATION)"""
        # "192.168.1.1" -> MTkyLjE2OC4xLjE=
        text = "Access via MTkyLjE2OC4xLjE="
        _assert_not_detected(text)

    def test_homoglyph_in_keyword(self):
        """Attempt: Use Cyrillic 'а' in 'password'. (KNOWN LIMITATION)"""
        # 'p' + Cyrillic 'а' + 'ssword'
        text = "p\u0430ssword=MySecretPass123"
        _assert_not_detected(text)

    def test_reversed_email(self):
        """Attempt: Reverse the email string. (KNOWN LIMITATION)"""
        text = "Contact moc.elpmaxe@tset for support."
        _assert_not_detected(text)

    def test_url_encoded_email(self):
        """Attempt: URL-encode the @ symbol. (KNOWN LIMITATION)"""
        text = "Email test%40example.com"
        _assert_not_detected(text)

    def test_split_across_newline(self):
        """Attempt: Split an email across a newline. (KNOWN LIMITATION)"""
        text = "Contact test\n@example.com immediately."
        # Currently, newline splitting breaks the regex since it requires adjacent characters.
        _assert_not_detected(text)
