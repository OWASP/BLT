from src.worker import (
    build_project_selection_blocks,
    build_repo_selection_blocks,
    interaction_response,
    project_response,
    render_team_join_message,
    repo_response,
    summarize_contributors,
    verify_slack_signature,
)


def test_verify_slack_signature_accepts_valid_request():
    secret = "signing-secret"
    timestamp = "1710000000"
    body = "token=value&command=%2Fproject"
    import hashlib
    import hmac

    expected = "v0=" + hmac.new(
        secret.encode("utf-8"),
        "v0:{0}:{1}".format(timestamp, body).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert verify_slack_signature(secret, timestamp, body, expected, now_ts=1710000000)


def test_verify_slack_signature_rejects_expired_request():
    assert not verify_slack_signature(
        "secret",
        "1710000000",
        "body",
        "v0=invalid",
        now_ts=1710000601,
    )


def test_project_response_without_query_returns_blocks():
    response = project_response("")
    assert response["blocks"]
    assert response["text"] == "Choose a project to inspect."


def test_repo_response_without_query_returns_blocks():
    response = repo_response("")
    assert response["blocks"]
    assert response["text"] == "Choose a technology to inspect."


def test_interaction_response_returns_project_detail():
    response = interaction_response(
        {
            "actions": [
                {
                    "action_id": "project_select_action_0",
                    "selected_option": {"value": "www-project-zap"},
                }
            ]
        }
    )
    assert "www-project-zap" in response["text"]


def test_build_blocks_are_chunked_and_capped():
    project_blocks = build_project_selection_blocks(["project-{0}".format(index) for index in range(201)])
    assert len(project_blocks) == 3

    repo_blocks = build_repo_selection_blocks({"python": ["https://example.com"]})
    assert len(repo_blocks) == 2


def test_summarize_contributors_sorts_by_total_activity():
    rows = summarize_contributors(
        [{"user": {"login": "alice"}}, {"user": {"login": "alice"}}],
        [{"user": {"login": "bob"}}],
        [{"user": {"login": "bob"}}, {"user": {"login": "bob"}}],
    )
    assert rows[0]["user"] == "bob"
    assert rows[0]["total"] == 3


def test_render_team_join_message_uses_team_template():
    message = render_team_join_message(
        {"user": {"id": "U123", "name": "newperson"}},
        "T04T40NHX",
    )
    assert message == "welcome newperson"