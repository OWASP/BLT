import pytest

from payload_redact import redact_payload, redact_value


def test_redacts_top_level_sensitive_key():
    result = redact_payload({"password": "hunter2", "host": "a.com"})
    assert result == {"password": "[REDACTED]", "host": "a.com"}


def test_key_match_is_case_insensitive():
    result = redact_payload({"Password": "x", "TOKEN": "y"})
    assert result == {"Password": "[REDACTED]", "TOKEN": "[REDACTED]"}


def test_redacts_inside_nested_dict():
    result = redact_payload({"auth": {"secret": "s", "user": "u"}})
    assert result == {"auth": {"secret": "[REDACTED]", "user": "u"}}


def test_redacts_inside_list_of_dicts():
    result = redact_payload({"items": [{"token": "t"}, {"name": "n"}]})
    assert result == {"items": [{"token": "[REDACTED]"}, {"name": "n"}]}


def test_sensitive_key_with_dict_value_is_redacted_whole():
    result = redact_payload({"credential": {"user": "u"}})
    assert result == {"credential": "[REDACTED]"}


@pytest.mark.parametrize("value", ["text", 5, None])
def test_non_dict_values_pass_through(value):
    assert redact_value(value) == value


def test_does_not_modify_input():
    payload = {"password": "hunter2"}
    redact_payload(payload)
    assert payload == {"password": "hunter2"}


def test_redacts_in_mixed_nested_collections():
    payload = {"groups": [[{"secret": "s"}], {"inner": [{"token": "t"}]}, "plain", 3]}
    assert redact_payload(payload) == {
        "groups": [[{"secret": "[REDACTED]"}], {"inner": [{"token": "[REDACTED]"}]}, "plain", 3]
    }


def test_sensitive_key_with_list_value_is_redacted_whole():
    assert redact_payload({"token": ["a", "b"]}) == {"token": "[REDACTED]"}


@pytest.mark.parametrize("payload", [{}, {"items": []}, {"auth": {}}])
def test_empty_collections_are_unchanged(payload):
    assert redact_payload(payload) == payload


# Only exact key names are matched, so these variants currently leak.
@pytest.mark.xfail(reason="access_token is not an exact match for 'token'", strict=True)
def test_access_token_is_redacted():
    assert redact_payload({"access_token": "t"}) == {"access_token": "[REDACTED]"}


@pytest.mark.xfail(reason="api-key uses a hyphen; REDACT_KEYS has api_key", strict=True)
def test_hyphenated_api_key_is_redacted():
    assert redact_payload({"api-key": "k"}) == {"api-key": "[REDACTED]"}
