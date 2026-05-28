from __future__ import annotations

import json
from typing import Any

import requests


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a chat-model response."""
    stripped = (text or "").strip()
    if not stripped:
        raise ValueError("Model response was empty.")

    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in model response: {text[:200]}")
    return json.loads(stripped[start : end + 1])


class OpenAICompatibleJsonClient:
    def __init__(self, *, model: str, base_url: str, api_key: str, timeout: int = 60):
        self.model = model
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.model and self.base_url and self.api_key)

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.is_configured:
            raise RuntimeError("Model client is not configured.")

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return extract_json_object(content)
