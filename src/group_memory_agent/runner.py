"""Agent runner interface."""

from __future__ import annotations

from typing import Protocol
import asyncio
import json
import requests

from .config import ModelConfig
from .models import ReplyRequest
from .prompts import build_reply_prompt


class AgentRunner(Protocol):
    async def reply(self, request: ReplyRequest) -> str:
        """Return the final text that should be sent to the group."""


class StubAgentRunner:
    async def reply(self, request: ReplyRequest) -> str:
        text = request.current.visible_text.replace("\n", " ").strip()
        return f"[stub:{request.trigger.reason}] 我收到了：{text[:120]}"


class OpenAICompatibleRunner:
    """Minimal OpenAI-compatible chat-completions runner.

    This intentionally does not implement arbitrary tools. Keep file access,
    local commands, and private-memory mutation outside the public gateway.
    """

    def __init__(self, config: ModelConfig, *, timeout: int = 180):
        self.config = config
        self.timeout = timeout

    async def reply(self, request: ReplyRequest) -> str:
        prompt = build_reply_prompt(request)
        return await asyncio.to_thread(self._call_sync, prompt)

    def _call_sync(self, prompt: str) -> str:
        if not self.config.api_key:
            raise RuntimeError(f"Missing API key env var: {self.config.api_key_env}")
        payload: dict = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.max_tokens,
        }
        if self.config.reasoning_effort:
            payload["reasoning_effort"] = self.config.reasoning_effort
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        if self.config.top_p is not None:
            payload["top_p"] = self.config.top_p
        response = requests.post(
            f"{self.config.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"].get("content", "")).strip()


class CommandAgentRunner:
    """Run an external command and pass the context pack through stdin as JSON."""

    def __init__(self, command: list[str], *, timeout: int = 180):
        self.command = command
        self.timeout = timeout

    async def reply(self, request: ReplyRequest) -> str:
        payload = {
            "prompt": build_reply_prompt(request),
            "group_id": request.group_id,
            "trigger_reason": request.trigger.reason,
        }
        proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
            timeout=self.timeout,
        )
        if proc.returncode:
            raise RuntimeError(stderr.decode("utf-8", errors="replace"))
        return stdout.decode("utf-8", errors="replace").strip()
