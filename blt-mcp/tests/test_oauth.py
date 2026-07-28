from blt_mcp.oauth import generate_code_challenge, generate_code_verifier


def test_generate_code_verifier():
    """Verify that verifier is a high-entropy URL-safe string of appropriate length."""
    verifier = generate_code_verifier()
    assert isinstance(verifier, str)
    assert len(verifier) >= 43 and len(verifier) <= 128
    # Ensure URL-safe characters
    allowed_chars = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"
    )
    assert all(c in allowed_chars for c in verifier)


def test_generate_code_challenge():
    """Verify code challenge generation matches specification (S256)."""
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    # S256 challenge for this exact verifier should be E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
    expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

    challenge = generate_code_challenge(verifier)
    assert challenge == expected_challenge
