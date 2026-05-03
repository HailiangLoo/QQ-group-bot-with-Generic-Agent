"""Minimal OneBot v11 WebSocket gateway."""

from __future__ import annotations

from typing import Any
import asyncio
import json
from pathlib import PurePosixPath, PureWindowsPath
import uuid

import websockets

from .config import AppConfig
from .live_memory import LiveMemory
from .models import ImageAttachment, IncomingMessage, ReplyRequest
from .runner import AgentRunner
from .self_improvement import SelfImprovementEvent, SelfImprovementQueue
from .trigger_policy import TriggerPolicy


class OneBotGateway:
    def __init__(self, config: AppConfig, memory: LiveMemory, runner: AgentRunner):
        self.config = config
        self.memory = memory
        self.runner = runner
        self.policy = TriggerPolicy(config.onebot, config.trigger)
        self.self_improvement = SelfImprovementQueue(config.memory.self_improvement_queue_path)
        self.delayed_tasks: dict[str, asyncio.Task] = {}

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
                    self.self_improvement.append(
                        SelfImprovementEvent(
                            event_type="gateway_error",
                            summary=f"{type(exc).__name__}: {exc}",
                            severity="medium",
                        )
                    )

    async def handle_event(self, ws: websockets.WebSocketClientProtocol, event: dict[str, Any]) -> None:
        message = parse_onebot_group_message(event)
        if message is None:
            return
        if not self._group_allowed(message.group_id):
            return

        if not self.config.memory.store_raw_events:
            message.raw = {}
        self.memory.add_message(message)
        pending = self.delayed_tasks.pop(message.group_id, None)
        if pending:
            pending.cancel()
        decision = self.policy.decide_basic(message)
        if not decision.should_reply:
            return

        if decision.wait_seconds:
            self._schedule_delayed_reply(ws, message, decision)
            return

        await self.reply_now(ws, message, decision)

    async def reply_now(
        self,
        ws: websockets.WebSocketClientProtocol,
        message: IncomingMessage,
        decision: Any,
    ) -> None:
        recent = self.memory.recent_messages(
            message.group_id,
            limit=self.config.memory.context_messages,
        )
        quote = self.memory.get_message_by_message_id(message.group_id, message.reply_to_message_id)
        if quote and all(item.row_id != quote.row_id for item in recent):
            # Bring the quoted message into view without exposing the whole database.
            anchor = self.memory.context_around_row(message.group_id, quote.row_id, before=10, after=30)
            recent = _merge_recent_context(anchor, recent, limit=200)
        request = ReplyRequest(
            group_id=message.group_id,
            current=message,
            recent_messages=recent,
            trigger=decision,
        )
        reply = await self.runner.reply(request)
        if not reply:
            return
        if reply.strip() in {"[NO_REPLY]", "NO_REPLY", "不回复"}:
            self.self_improvement.append(
                SelfImprovementEvent(
                    event_type="no_reply",
                    summary="Model decided not to reply to an automatic/follow-up candidate",
                    group_id=message.group_id,
                    user_id=message.user_id,
                    message_id=message.message_id,
                    metadata={"trigger_reason": decision.reason, "trigger_mode": decision.mode},
                )
            )
            return

        await self.send_group_msg(
            ws,
            message.group_id,
            reply,
            reply_to_message_id=message.message_id if self.config.onebot.reply_with_quote else "",
        )
        self.memory.add_agent_reply(message.group_id, reply)
        self.policy.arm_followup(message.group_id, reply)

    def _schedule_delayed_reply(
        self,
        ws: websockets.WebSocketClientProtocol,
        message: IncomingMessage,
        decision: Any,
    ) -> None:
        old = self.delayed_tasks.pop(message.group_id, None)
        if old:
            old.cancel()
        self.delayed_tasks[message.group_id] = asyncio.create_task(
            self._delayed_reply(ws, message, decision)
        )

    async def _delayed_reply(
        self,
        ws: websockets.WebSocketClientProtocol,
        message: IncomingMessage,
        decision: Any,
    ) -> None:
        try:
            await asyncio.sleep(float(decision.wait_seconds or 0))
            if self.delayed_tasks.get(message.group_id) is not asyncio.current_task():
                return
            self.delayed_tasks.pop(message.group_id, None)
            await self.reply_now(ws, message, decision)
        except asyncio.CancelledError:
            return

    async def send_group_msg(
        self,
        ws: websockets.WebSocketClientProtocol,
        group_id: str,
        text: str,
        *,
        reply_to_message_id: str = "",
    ) -> None:
        message: str | list[dict[str, Any]]
        if reply_to_message_id:
            message = [
                {"type": "reply", "data": {"id": reply_to_message_id}},
                {"type": "text", "data": {"text": text}},
            ]
        else:
            message = text
        payload = {
            "action": "send_group_msg",
            "params": {
                "group_id": int(group_id) if group_id.isdigit() else group_id,
                "message": message,
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

    text, images, reply_to_message_id = parse_segments(segments, fallback=str(event.get("raw_message", "")))
    return IncomingMessage(
        platform="onebot",
        group_id=group_id,
        user_id=user_id,
        nickname=nickname,
        text=text,
        message_id=message_id,
        reply_to_message_id=reply_to_message_id,
        images=images,
        raw=redact_onebot_event(event),
    )


def parse_segments(segments: Any, *, fallback: str = "") -> tuple[str, list[ImageAttachment], str]:
    if isinstance(segments, str):
        return segments, [], ""
    if not isinstance(segments, list):
        return fallback, [], ""

    texts: list[str] = []
    images: list[ImageAttachment] = []
    reply_to_message_id = ""
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
        elif seg_type == "reply":
            reply_to_message_id = str(data.get("id") or data.get("message_id") or "")
            texts.append("[引用消息]")
        elif seg_type == "image":
            images.append(
                ImageAttachment(
                    source=str(data.get("url") or data.get("file") or ""),
                    file_id=str(data.get("file", "")),
                    source_segment_type="image",
                )
            )
            texts.append("[图片]")
        elif seg_type == "file" and looks_like_image_file_segment(data):
            images.append(
                ImageAttachment(
                    source=str(data.get("url") or data.get("file") or ""),
                    file_id=str(data.get("file", "")),
                    source_segment_type="file",
                )
            )
            texts.append("[图片文件]")
        elif seg_type in {"file", "video", "record"}:
            texts.append("[QQ文件/音视频已屏蔽]")
    return "".join(texts).strip(), images, reply_to_message_id


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic", ".heif"}
SENSITIVE_SEGMENT_KEYS = {"url", "file", "path", "file_id", "token", "cookie"}


def looks_like_image_file_segment(data: dict[str, Any]) -> bool:
    name = str(data.get("name") or data.get("file") or data.get("url") or "").split("?", 1)[0]
    try:
        size = int(data.get("file_size") or data.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    if size and size > 10 * 1024 * 1024:
        return False
    ext = PureWindowsPath(name).suffix.lower() or PurePosixPath(name).suffix.lower()
    return ext in IMAGE_EXTENSIONS


def redact_onebot_event(event: dict[str, Any]) -> dict[str, Any]:
    """Keep raw event shape useful for debugging without storing transport secrets."""
    safe = dict(event)
    message = safe.get("message")
    if isinstance(message, list):
        redacted = []
        for segment in message:
            if not isinstance(segment, dict):
                continue
            item = {"type": segment.get("type"), "data": {}}
            data = segment.get("data") or {}
            if isinstance(data, dict):
                item["data"] = {
                    key: ("[redacted]" if key in SENSITIVE_SEGMENT_KEYS else value)
                    for key, value in data.items()
                }
            redacted.append(item)
        safe["message"] = redacted
    return safe


def _merge_recent_context(
    first: list[Any],
    second: list[Any],
    *,
    limit: int,
) -> list[Any]:
    by_id = {}
    for item in [*first, *second]:
        by_id[getattr(item, "row_id", id(item))] = item
    merged = sorted(by_id.values(), key=lambda item: getattr(item, "row_id", 0))
    return merged[-limit:]
