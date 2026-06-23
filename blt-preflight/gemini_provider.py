"""
Gemini Flash Provider (Week 2)
--------------------------------
Thin wrapper around the Gemini API. Returns raw JSON text; schema validation
happens one layer up in advisory_generator.py so the provider stays
swappable (OpenAI / Ollama fallback can implement the same interface).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("blt_preflight.llm.gemini")

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)

DEFAULT_TIMEOUT_SECONDS = 8
MAX_RETRIES = 2


class LLMCallError(Exception):
    """Raised when the LLM call fails after retries (triggers fallback)."""


class GeminiProvider:
    name = "gemini-flash"

    def __init__(self, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.timeout = timeout

    def _post(self, system_prompt: str, user_prompt: str) -> dict:
        import requests  # local import keeps this optional at module load time

        if not self.api_key:
            raise LLMCallError("GEMINI_API_KEY not set")

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 800,
                "responseMimeType": "application/json",
            },
        }
        resp = requests.post(
            f"{GEMINI_API_URL}?key={self.api_key}",
            json=payload,
            timeout=self.timeout,
        )

        # Fallback trigger conditions per proposal: HTTP 429 or 5xx
        if resp.status_code == 429 or resp.status_code >= 500:
            raise LLMCallError(f"Gemini returned retryable status {resp.status_code}")
        resp.raise_for_status()
        return resp.json()

    def generate(self, system_prompt: str, user_prompt: str) -> tuple[str, int]:
        """
        Returns (raw_json_text, generation_time_ms).
        Raises LLMCallError on failure after retries — caller decides fallback.
        """
        last_err: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            start = time.monotonic()
            try:
                data = self._post(system_prompt, user_prompt)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                if not text:
                    raise LLMCallError("Empty response from Gemini")
                return text, elapsed_ms
            except LLMCallError as e:
                last_err = e
                logger.warning("Gemini call attempt %d/%d failed: %s", attempt, MAX_RETRIES, e)
                time.sleep(0.5 * attempt)
            except Exception as e:  # network errors, timeouts, etc.
                last_err = e
                logger.warning("Gemini call attempt %d/%d errored: %s", attempt, MAX_RETRIES, e)
                time.sleep(0.5 * attempt)

        raise LLMCallError(f"Gemini call failed after {MAX_RETRIES} attempts: {last_err}")


def parse_json_strict(raw_text: str) -> dict:
    """Strip accidental markdown fences and parse. No silent repair of bad JSON —
    if it doesn't parse, the caller should fall back, not guess."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())