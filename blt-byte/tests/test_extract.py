import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import _extract_ai_text
import pytest


class TestExtractAiText:

    # --- OpenAI choices shape ---
    def test_openai_choices_string_content(self):
        response = {"choices": [{"message": {"content": "Hello world"}}]}
        assert _extract_ai_text(response) == "Hello world"

    def test_openai_choices_list_content(self):
        response = {"choices": [{"message": {"content": [
            {"type": "text", "text": "Part one "},
            {"type": "text", "text": "part two"},
        ]}}]}
        result = _extract_ai_text(response)
        assert "Part one" in result
        assert "part two" in result

    def test_openai_choices_skips_non_text_parts(self):
        response = {"choices": [{"message": {"content": [
            {"type": "image", "url": "http://img"},
            {"type": "text", "text": "Text only"},
        ]}}]}
        result = _extract_ai_text(response)
        assert result == "Text only"

    # --- Cloudflare Workers AI shape ---
    def test_cloudflare_response_key(self):
        result = _extract_ai_text({"response": "CF answer"})
        assert result == "CF answer"

    def test_output_key_takes_priority_over_response(self):
        response = {
            "output": [{"role": "assistant", "content": "Output answer"}],
            "response": "Should be ignored"
        }
        result = _extract_ai_text(response)
        assert result == "Output answer"

    # --- list-output shape ---
    def test_list_output_assistant_string_content(self):
        response = {"output": [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"}
        ]}
        assert _extract_ai_text(response) == "Answer"

    def test_list_output_skips_non_assistant_roles(self):
        response = {"output": [
            {"role": "user", "content": "Should be skipped"},
        ]}
        assert _extract_ai_text(response) is None

    def test_list_output_assistant_list_content(self):
        response = {"output": [{"role": "assistant", "content": [
            {"type": "output_text", "text": "Assembled answer"}
        ]}]}
        assert _extract_ai_text(response) == "Assembled answer"

    # --- dict fallback keys ---
    def test_reply_key(self):
        assert _extract_ai_text({"reply": "Reply text"}) == "Reply text"

    def test_text_key(self):
        assert _extract_ai_text({"text": "Text value"}) == "Text value"

    def test_content_key(self):
        assert _extract_ai_text({"content": "Content value"}) == "Content value"

    # --- plain string ---
    def test_plain_string(self):
        assert _extract_ai_text("Plain string response") == "Plain string response"

    # --- None / unknown shapes ---
    def test_none_input(self):
        assert _extract_ai_text(None) is None

    def test_empty_dict(self):
        assert _extract_ai_text({}) is None

    def test_empty_list(self):
        assert _extract_ai_text([]) is None

    def test_integer_input(self):
        assert _extract_ai_text(42) is None

    def test_empty_choices(self):
        assert _extract_ai_text({"choices": []}) is None

    # --- sanitization is applied ---
    def test_reasoning_stripped_from_extracted_text(self):
        response = {"response": "<think>internal</think>Clean answer"}
        result = _extract_ai_text(response)
        assert "internal" not in result
        assert "Clean answer" in result

    def test_returns_none_when_only_reasoning_in_response(self):
        response = {"response": "<think>all internal</think>"}
        result = _extract_ai_text(response)
        assert result is None or (result is not None and "all internal" not in result)
