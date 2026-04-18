from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from backend.config import Settings, get_settings


class DeepSeekClientError(RuntimeError):
    """Raised when the DeepSeek adapter cannot produce a JSON response."""


class DeepSeekClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def chat_json(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        timeout: float = 30.0
    ) -> dict[str, Any]:
        if not self.settings.deepseek_api_key:
            raise DeepSeekClientError("DEEPSEEK_API_KEY is not configured.")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model or self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }

        endpoint = f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions"
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.deepseek_api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw_response = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise DeepSeekClientError(
                f"DeepSeek request failed with status {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise DeepSeekClientError(f"DeepSeek request could not be completed: {exc.reason}") from exc

        try:
            content = raw_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekClientError("DeepSeek response did not include message content.") from exc

        return self._coerce_json(content)

    def _coerce_json(self, content: Any) -> dict[str, Any]:
        if isinstance(content, dict):
            return content

        if isinstance(content, list):
            text = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        else:
            text = str(content)

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise DeepSeekClientError("DeepSeek response was not valid JSON.") from exc
            parsed = json.loads(cleaned[start : end + 1])

        if not isinstance(parsed, dict):
            raise DeepSeekClientError("DeepSeek JSON response must decode to an object.")

        return parsed

