"""Minimal OneBot v11 WebSocket gateway."""

from __future__ import annotations

from typing import Any
import asyncio
import json
import uuid

import websockets

from .config import AppConfig
from .live_memory import LiveMemory
from .models import ImageAttachment, IncomingMessage, ReplyRequest
from .runner import AgentRunner
from .trigger_policy import TriggerPolicy


class OneBotGateway:
    def __init__(self, config: AppConfig, memory: LiveMemory, runner: AgentRunner):
        self.config = config
        self.memory = memory
        self.runner = runner
        self.policy = TriggerPolicy(config.onebot, config.trigger)

    async def run_forever(self) -> None:
        headers = {}
        if self.config.onebot.access_token:
            headers["Authorization"] = f"Bearer {self.config.onebot.access_token}"

        try:
            await self._run_loop(headers, header_kwarg="additional_headers")
        except TypeError as exc:
            # websockets 12 used extra_headers; newer versions use additional_headers.
            if "additional_headers" not in str(exc):
                raise
            await self._run_loop(headers, header_kwarg="extra_headers")

    async def _run_loop(self, headers: dict[str, str], *, header_kwarg: str) -> None:
        kwargs: dict[str, Any] = {
            "ping_interval": 30,
            "ping_timeout": 30,
        }
        if headers:
            kwargs[header_kwarg] = headers

        async with websockets.connect(
            self.config.onebot.ws_url,
            **kwargs,
        ) as ws:
            async for raw in ws:
                try:
                    event = json.loads(raw)
                    await self.handle_event(ws, event)
                except Exception as exc:  # keep gateway alive
                    print(f"[gateway] event error: {exc}")

    async def handle_event(self, ws: websockets.WebSocketClientProtocol, event: dict[str, Any]) -> None:
        message = parse_onebot_group_message(event)
        if message is None:
            return
        if not self._group_allowed(message.group_id):
            return

        self.memory.add_message(message)
        decision = self.policy.decide_basic(message)
        if not decision.should_reply:
            return

        if decision.wait_seconds:
            await asyncio.sleep(decision.wait_seconds)

        recent = self.memory.recent_messages(
            message.group_id,
            limit=self.config.memory.context_messages,
        )
        request = ReplyRequest(
            group_id=message.group_id,
            current=message,
            recent_messages=recent,
            trigger=decision,
        )
        reply = await self.runner.reply(request)
        if not reply:
            return

        await self.send_group_msg(ws, message.group_id, reply)
        self.memory.add_agent_reply(message.group_id, reply)
        self.policy.arm_followup(message.group_id, reply)

    async def send_group_msg(self, ws: websockets.WebSocketClientProtocol, group_id: str, text: str) -> None:
        payload = {
            "action": "send_group_msg",
            "params": {
                "group_id": int(group_id) if group_id.isdigit() else group_id,
                "message": text,
            },
            "echo": str(uuid.uuid4()),
        }
        await ws.send(json.dumps(payload, ensure_ascii=False))

    def _group_allowed(self, group_id: str) -> bool:
        allowed = self.config.onebot.allowed_groups
        return "*" in allowed or group_id in allowed


def parse_onebot_group_message(event: dict[str, Any]) -> IncomingMessage | None:
    if event.get("post_type") != "message":
        return None
    if event.get("message_type") != "group":
        return None

    group_id = str(event.get("group_id", ""))
    user_id = str(event.get("user_id", ""))
    sender = event.get("sender") or {}
    nickname = str(sender.get("card") or sender.get("nickname") or user_id)
    message_id = str(event.get("message_id", ""))
    segments = event.get("message")

    text, images = parse_segments(segments, fallback=str(event.get("raw_message", "")))
    return IncomingMessage(
        platform="onebot",
        group_id=group_id,
        user_id=user_id,
        nickname=nickname,
        text=text,
        message_id=message_id,
        images=images,
        raw=event,
    )


def parse_segments(segments: Any, *, fallback: str = "") -> tuple[str, list[ImageAttachment]]:
    if isinstance(segments, str):
        return segments, []
    if not isinstance(segments, list):
        return fallback, []

    texts: list[str] = []
    images: list[ImageAttachment] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        seg_type = segment.get("type")
        data = segment.get("data") or {}
        if seg_type == "text":
            texts.append(str(data.get("text", "")))
        elif seg_type == "at":
            qq = str(data.get("qq", ""))
            texts.append(f"@{qq}" if qq else "@")
        elif seg_type == "image":
            images.append(
                ImageAttachment(
                    source=str(data.get("url") or data.get("file") or ""),
                    file_id=str(data.get("file", "")),
                )
            )
            texts.append("[图片]")
    return "".join(texts).strip(), images
