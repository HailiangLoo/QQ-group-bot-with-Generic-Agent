"""Trigger policy primitives."""

from __future__ import annotations

from dataclasses import dataclass
import random
import time

from .config import OneBotConfig, TriggerConfig
from .models import IncomingMessage, TriggerDecision


@dataclass(slots=True)
class FollowupState:
    remaining: int
    expires_at: float
    last_reply_text: str
    last_reply_at: float


class TriggerPolicy:
    def __init__(self, onebot: OneBotConfig, trigger: TriggerConfig):
        self.onebot = onebot
        self.trigger = trigger
        self.followups: dict[str, FollowupState] = {}
        self.last_auto_reply_at: dict[str, float] = {}
        self.hourly_counts: dict[tuple[str, int], int] = {}

    def decide_basic(self, message: IncomingMessage, *, is_agent_message: bool = False) -> TriggerDecision:
        if is_agent_message:
            return TriggerDecision(False, "ignore self", 0.0, mode="ignore")

        if self.has_explicit_trigger(message.text):
            return TriggerDecision(True, "explicit trigger word", 1.0, mode="explicit")

        followup = self.consume_followup_slot(message.group_id)
        if followup:
            if self.can_reply_after_last_agent_message(message.group_id):
                return TriggerDecision(
                    True,
                    "follow-up candidate after agent reply",
                    0.55,
                    self.trigger.followup_wait_seconds,
                    mode="followup",
                )
            return TriggerDecision(False, "follow-up cooldown", 0.0, mode="followup")

        if len(message.text.strip()) >= self.trigger.long_text_chars:
            return TriggerDecision(
                True,
                "long text summary candidate",
                0.65,
                self.trigger.long_text_wait_seconds,
                mode="auto_long_text",
            )

        if self._keyword_banter_allowed(message):
            return TriggerDecision(True, "light keyword/random banter", 0.35, mode="auto_banter")

        return TriggerDecision(False, "no trigger", 0.0, mode="none")

    def has_explicit_trigger(self, text: str) -> bool:
        return any(word and word in text for word in self.onebot.trigger_words)

    def arm_followup(self, group_id: str, reply_text: str) -> None:
        now = time.time()
        self.followups[group_id] = FollowupState(
            remaining=self.trigger.followup_messages,
            expires_at=now + self.trigger.followup_ttl_seconds,
            last_reply_text=reply_text,
            last_reply_at=now,
        )

    def consume_followup_slot(self, group_id: str) -> FollowupState | None:
        state = self.followups.get(group_id)
        if not state:
            return None
        now = time.time()
        if state.expires_at < now or state.remaining <= 0:
            self.followups.pop(group_id, None)
            return None
        state.remaining -= 1
        return state

    def can_reply_after_last_agent_message(self, group_id: str) -> bool:
        state = self.followups.get(group_id)
        if not state:
            return True
        return (time.time() - state.last_reply_at) >= self.trigger.followup_min_reply_cooldown

    def _keyword_banter_allowed(self, message: IncomingMessage) -> bool:
        text = message.text.strip()
        if len(text) < self.trigger.idle_reply_min_chars:
            return False
        if self.trigger.keywords and not any(keyword in text for keyword in self.trigger.keywords):
            return False
        now = time.time()
        last = self.last_auto_reply_at.get(message.group_id, 0.0)
        if now - last < self.trigger.auto_reply_min_interval:
            return False
        hour_key = (message.group_id, int(now // 3600))
        if self.trigger.auto_reply_max_per_hour > 0 and self.hourly_counts.get(hour_key, 0) >= self.trigger.auto_reply_max_per_hour:
            return False
        if random.random() > self.trigger.auto_reply_chance:
            return False
        self.last_auto_reply_at[message.group_id] = now
        self.hourly_counts[hour_key] = self.hourly_counts.get(hour_key, 0) + 1
        return True
