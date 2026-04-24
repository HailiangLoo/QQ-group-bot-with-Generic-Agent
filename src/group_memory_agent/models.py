"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import time


@dataclass(slots=True)
class ImageAttachment:
    source: str
    file_id: str = ""
    local_path: str = ""
    sha256: str = ""
    caption: str = ""


@dataclass(slots=True)
class IncomingMessage:
    platform: str
    group_id: str
    user_id: str
    nickname: str
    text: str
    message_id: str = ""
    timestamp: float = field(default_factory=time.time)
    images: list[ImageAttachment] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def visible_text(self) -> str:
        parts = [self.text.strip()]
        for image in self.images:
            if image.caption:
                parts.append(f"[图片: {image.caption.strip()}]")
            elif image.source:
                parts.append("[图片]")
        return "\n".join(part for part in parts if part)


@dataclass(slots=True)
class StoredMessage:
    row_id: int
    group_id: str
    user_id: str
    nickname: str
    role: str
    text: str
    created_at: float


@dataclass(slots=True)
class TriggerDecision:
    should_reply: bool
    reason: str
    confidence: float = 1.0
    wait_seconds: float = 0.0


@dataclass(slots=True)
class ReplyRequest:
    group_id: str
    current: IncomingMessage
    recent_messages: list[StoredMessage]
    trigger: TriggerDecision
    memory_snippets: list[str] = field(default_factory=list)

