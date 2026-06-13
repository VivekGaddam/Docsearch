from __future__ import annotations

import json
import re
from typing import Any

import httpx

# Gemini REST API endpoint (native — more reliable than OpenAI compat layer)
_GEMINI_REST_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
_DEFAULT_MODEL = "gemini-1.5-flash"       # stable, free, fast


class LLMService:
    """
    Gemini-first LLM client.

    Strategy:
      1. If GEMINI_API_KEY set  → use Gemini native REST API (reliable)
      2. If OPENAI_API_KEY set  → use OpenAI-compatible endpoint
      3. Neither                → smart fallback (no LLM)

    We use the NATIVE Gemini REST endpoint (not the OpenAI compat shim)
    because the compat layer returns 500 errors for some models/payloads.
    """

    # ── Live config properties (re-read every call, no cache issues) ───────

    @property
    def _gemini_key(self) -> str | None:
        from app.core.config import settings
        return settings.gemini_api_key or None

    @property
    def _openai_key(self) -> str | None:
        from app.core.config import settings
        return settings.openai_api_key or None

    @property
    def _model(self) -> str:
        from app.core.config import settings
        m = (settings.llm_model or "").strip()
        # If model looks like an OpenAI model name, switch to Gemini default
        if not m or m.startswith("gpt-"):
            return _DEFAULT_MODEL
        return m

    def is_available(self) -> bool:
        return bool(self._gemini_key or self._openai_key)

    def active_provider(self) -> str:
        if self._gemini_key:
            return f"gemini-native ({self._model})"
        if self._openai_key:
            from app.core.config import settings
            return f"openai ({self._model})"
        return "none"

    # ── Public API ────────────────────────────────────────────────────────

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        if self._gemini_key:
            return self._gemini_chat(system, user, temperature)
        if self._openai_key:
            return self._openai_chat(system, user, temperature)
        return ""

    def chat_json(self, system: str, user: str) -> dict[str, Any] | None:
        raw = self.chat(system, user + "\n\nRespond with valid JSON only.", temperature=0.1)
        if not raw:
            return None
        cleaned = raw.strip()
        # Strip ```json ... ``` fences that Gemini sometimes adds
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            return None

    # ── Gemini native REST ─────────────────────────────────────────────────

    def _gemini_chat(self, system: str, user: str, temperature: float) -> str:
        """
        Uses the Gemini generateContent REST endpoint directly.
        More reliable than the OpenAI-compatibility shim.
        """
        model = self._model
        api_key = self._gemini_key
        url = f"{_GEMINI_REST_BASE}/{model}:generateContent?key={api_key}"

        # Gemini REST payload format
        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system}\n\n{user}"}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096,
            },
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # Extract text from Gemini response
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()

            print(f"[LLMService] Gemini empty response: {data}")
            return ""

        except httpx.HTTPStatusError as e:
            body = e.response.text[:400]
            print(f"[LLMService] Gemini HTTP {e.response.status_code}: {body}")

            # If the model name is wrong, try the stable fallback model
            if e.response.status_code in (400, 404) and model != _DEFAULT_MODEL:
                print(f"[LLMService] Retrying with fallback model {_DEFAULT_MODEL}…")
                url2 = f"{_GEMINI_REST_BASE}/{_DEFAULT_MODEL}:generateContent?key={api_key}"
                try:
                    with httpx.Client(timeout=120.0) as client:
                        resp2 = client.post(url2, json=payload)
                        resp2.raise_for_status()
                        data2 = resp2.json()
                    candidates2 = data2.get("candidates", [])
                    if candidates2:
                        parts2 = candidates2[0].get("content", {}).get("parts", [])
                        if parts2:
                            return parts2[0].get("text", "").strip()
                except Exception as e2:
                    print(f"[LLMService] Fallback also failed: {e2}")
            return ""

        except Exception as e:
            print(f"[LLMService] Gemini error: {type(e).__name__}: {e}")
            return ""

    # ── OpenAI-compatible fallback ─────────────────────────────────────────

    def _openai_chat(self, system: str, user: str, temperature: float) -> str:
        from app.core.config import settings
        api_key = self._openai_key
        base_url = settings.openai_base_url.rstrip("/")
        model = self._model

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            print(f"[LLMService] OpenAI HTTP {e.response.status_code}: {e.response.text[:300]}")
            return ""
        except Exception as e:
            print(f"[LLMService] OpenAI error: {e}")
            return ""


llm_service = LLMService()
