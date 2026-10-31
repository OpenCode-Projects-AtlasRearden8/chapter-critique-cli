"""Minimal OpenAI-compatible chat-completions client.

Works with any server that implements POST {base_url}/chat/completions,
including Ollama (http://localhost:11434), LM Studio, llama.cpp server,
vLLM, and OpenAI itself. No API keys are read, stored, or sent.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    """Anything with a .chat(messages) -> str method."""

    def chat(self, messages: list[dict]) -> str: ...


@dataclass
class OpenAICompatibleClient:
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    temperature: float = 0.4
    max_tokens: int = 2048
    timeout_seconds: float = 120.0

    @property
    def endpoint_url(self) -> str:
        base = self.base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        return f"{base}/chat/completions"

    def chat(self, messages: list[dict]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        req = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as err:
            raise RuntimeError(
                f"Could not reach {self.endpoint_url} ({err.reason or err}).\n"
                "Is the endpoint running? For Ollama: `ollama serve`, then\n"
                "`ollama pull <model>`. Or run with --no-llm for a stats-only critique."
            ) from err
        except json.JSONDecodeError as err:
            raise RuntimeError(f"Endpoint returned non-JSON output: {err}") from err
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as err:
            raise RuntimeError(
                f"Unexpected response shape from endpoint: {json.dumps(body)[:400]}"
            ) from err


class NullClient:
    """Offline stand-in used with --no-llm; never calls any endpoint."""

    def chat(self, messages: list[dict]) -> str:
        raise RuntimeError("NullClient must not be called")
