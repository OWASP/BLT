from domain_normalize import normalize_domain


def test_normalize_strips_www_protocol_slash_and_case():
    a = normalize_domain("HTTPS://WWW.Example.COM/path?q=1")
    b = normalize_domain("http://example.com/")
    c = normalize_domain("example.com")
    assert a == ("example.com", "https://example.com/")
    assert b == a
    assert c == a


def test_normalize_rejects_localhost_and_schemes():
    assert normalize_domain("http://localhost/") is None
    assert normalize_domain("mailto:sec@example.com") is None
    assert normalize_domain("") is None
