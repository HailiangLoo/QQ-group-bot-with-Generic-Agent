"""Proposal-only self-improvement event queue.

The gateway may record mistakes, corrections, failed image captions, search
misses, duplicate replies, or transport errors here. A separate review step can
turn these events into memory/profile/prompt changes. Runtime code should not
silently rewrite long-term memory from QQ chat.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json
import time


@dataclass(slots=True)
class SelfImprovementEvent:
    event_type: str
    summary: str
    severity: str = "low"
    created_at: float = field(default_factory=time.time)
    group_id: str = ""
    user_id: str = ""
    message_id: str = ""
    evidence: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class SelfImprovementQueue:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: SelfImprovementEvent) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(event), ensure_ascii=False, sort_keys=True) + "\n")

