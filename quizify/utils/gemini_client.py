"""
Groq API client wrapper used by all 4 agents.

Named GeminiClient / get_gemini_client intentionally so that
nothing in agents/ needs to change -- the public interface is
identical, only the underlying API call changed.

Uses llama-3.3-70b-versatile by default:
  - 14,400 free requests/day (vs Gemini free tier's very limited quota)
  - Excellent at structured JSON output (needed for quiz generation)
  - Faster responses than Gemini 2.5 Pro
  - No billing setup required

Switch model in .env: GROQ_MODEL=llama-3.3-70b-versatile
Other good options: mixtral-8x7b-32768, llama-3.1-8b-instant (fastest/cheapest)
"""
import sys
import json
import re
from pathlib import Path
from typing import Optional
import time

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import settings

from groq import Groq


class GeminiClient:
    """
    Named GeminiClient so all agent imports work without changes.
    Internally uses Groq's API.
    """

    def __init__(self, model_name: Optional[str] = None):
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file. "
                "Get a free key at https://console.groq.com "
                "(no billing required -- 14,400 requests/day free)"
            )
        self.client = Groq(api_key=settings.groq_api_key)
        self.model_name = model_name or settings.groq_model

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> str:
        """Plain text generation with retry on transient failures."""
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        last_err = None
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=4096,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Groq generation failed after {max_retries} attempts: {last_err}")

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.5,
        max_retries: int = 3,
    ) -> dict:
        """
        Request strict JSON output using Groq's JSON mode.
        Groq's json_object response_format is very reliable -- 
        rarely produces malformed JSON unlike plain text prompting.
        """
        system_content = "You must respond with valid JSON only. No markdown fences, no explanation, no preamble."
        if system_instruction:
            system_content = system_instruction + "\n\n" + system_content

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]

        last_err = None
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=4096,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content.strip()
                # strip any accidental markdown fences just in case
                raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.MULTILINE)
                return json.loads(raw)
            except Exception as e:
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(
            f"Groq JSON generation failed after {max_retries} attempts: {last_err}"
        )


_client_instance: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """
    Singleton accessor.
    Name kept as get_gemini_client so agent imports need no changes.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = GeminiClient()
    return _client_instance
