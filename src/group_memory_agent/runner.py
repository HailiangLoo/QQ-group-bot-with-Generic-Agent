"""Agent runner interface."""

from __future__ import annotations

from typing import Protocol
import asyncio
import json

from .models import ReplyRequest
from .prompts import build_reply_prompt


class AgentRunner(Protocol):
    async def reply(self, request: ReplyRequest) -> str:
        """Return the final text that should be sent to the group."""


class StubAgentRunner:
    async def reply(self, request: ReplyRequest) -> str:
        text = request.current.visible_text.replace("\n", " ").strip()
        return f"[stub:{request.trigger.reason}] 我收到了：{text[:120]}"


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

