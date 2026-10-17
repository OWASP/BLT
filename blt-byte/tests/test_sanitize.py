import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import _sanitize_ai_output
import pytest


class TestSanitizeAiOutput:

    # --- reasoning block stripping ---
    def test_strips_think_block(self):
        result = _sanitize_ai_output("<think>internal monologue</think>Here is the answer.")
        assert "internal monologue" not in result
        assert "Here is the answer." in result

    def test_strips_reasoning_block(self):
        result = _sanitize_ai_output("<reasoning>step 1\nstep 2</reasoning>Final answer.")
        assert "step 1" not in result
        assert "Final answer." in result

    def test_strips_analysis_block(self):
        result = _sanitize_ai_output("<analysis>private</analysis>Public response.")
        assert "private" not in result
        assert "Public response." in result

    def test_strips_multiline_think_block(self):
        text = "<think>\nLine 1\nLine 2\n</think>\nUser-facing text."
        result = _sanitize_ai_output(text)
        assert "Line 1" not in result
        assert "User-facing text." in result

    def test_strips_reasoning_preamble(self):
        text = "Reasoning:\nI need to think about this.\nHere is my answer."
        result = _sanitize_ai_output(text)
        assert result is not None
        # Preamble label should be gone
        assert not result.lower().startswith("reasoning:")

    def test_strips_chain_of_thought_preamble(self):
        text = "Chain of Thought: Let me reason...\nActual answer here."
        result = _sanitize_ai_output(text)
        assert "Actual answer here." in result

    # --- preservation ---
    def test_preserves_normal_markdown(self):
        md = "## How to report\n1. Step one\n2. Step two\n**Bold text**"
        result = _sanitize_ai_output(md)
        assert result == md

    def test_preserves_code_blocks(self):
        text = "Use `/api/scan` endpoint.\n```python\nprint('hello')\n```"
        result = _sanitize_ai_output(text)
        assert "`/api/scan`" in result
        assert "print('hello')" in result

    # --- edge cases ---
    def test_returns_none_for_empty_string(self):
        assert _sanitize_ai_output("") is None

    def test_returns_none_when_only_reasoning_remains(self):
        result = _sanitize_ai_output("<think>everything is internal</think>")
        # After stripping, nothing of substance remains
        assert result is None or result.strip() == ""

    def test_returns_none_for_whitespace_only(self):
        assert _sanitize_ai_output("   \n  ") is None

    def test_case_insensitive_tag_stripping(self):
        result = _sanitize_ai_output("<THINK>hidden</THINK>Visible.")
        assert "hidden" not in result
        assert "Visible." in result
