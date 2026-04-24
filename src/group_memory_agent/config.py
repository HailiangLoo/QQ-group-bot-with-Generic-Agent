"""Configuration loading for the gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os
import tomllib


@dataclass(slots=True)
class OneBotConfig:
    ws_url: str = "ws://127.0.0.1:3001"
    access_token: str = ""
    allowed_groups: list[str] = field(default_factory=lambda: ["*"])
    trigger_words: list[str] = field(default_factory=lambda: ["杰出"])


@dataclass(slots=True)
class MemoryConfig:
    db_path: Path = Path("data/live_memory.db")
    media_dir: Path = Path("data/media")
    context_messages: int = 80
    context_image_caption_clip: int = 520


@dataclass(slots=True)
class ModelConfig:
    name: str
    api_base: str
    api_key_env: str
    model: str
    max_tokens: int = 4096
    reasoning_effort: str | None = None

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


@dataclass(slots=True)
class TriggerConfig:
    followup_messages: int = 6
    followup_ttl_seconds: int = 600
    followup_context_messages: int = 8
    followup_reply_threshold: float = 0.72
    followup_wait_threshold: float = 0.45
    followup_wait_seconds: int = 6
    followup_min_reply_cooldown: int = 12

    auto_reply_min_interval: int = 300
    auto_reply_chance: float = 0.25
    auto_reply_max_per_hour: int = 10
    idle_new_topic_gap_seconds: int = 900
    idle_new_topic_wait_seconds: int = 120
    long_text_chars: int = 300
    long_text_wait_seconds: int = 45
    keywords: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppConfig:
    base_dir: Path
    onebot: OneBotConfig
    memory: MemoryConfig
    text_model: ModelConfig
    vision_model: ModelConfig
    trigger: TriggerConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    base_dir = config_path.parent
    onebot_raw = raw.get("onebot", {})
    memory_raw = raw.get("memory", {})
    models_raw = raw.get("models", {})
    trigger_raw = raw.get("trigger", {})

    onebot = OneBotConfig(
        ws_url=str(onebot_raw.get("ws_url", "ws://127.0.0.1:3001")),
        access_token=str(onebot_raw.get("access_token", "")),
        allowed_groups=_string_list(onebot_raw.get("allowed_groups", ["*"])),
        trigger_words=_string_list(onebot_raw.get("trigger_words", ["杰出"])),
    )

    memory = MemoryConfig(
        db_path=_resolve_path(memory_raw.get("db_path", "data/live_memory.db"), base_dir),
        media_dir=_resolve_path(memory_raw.get("media_dir", "data/media"), base_dir),
        context_messages=int(memory_raw.get("context_messages", 80)),
        context_image_caption_clip=int(memory_raw.get("context_image_caption_clip", 520)),
    )

    text_model = _model_config(
        models_raw.get("text", {}),
        fallback_name="deepseek-v4-flash",
        fallback_base="https://api.deepseek.com",
        fallback_env="TEXT_MODEL_API_KEY",
        fallback_model="deepseek-v4-flash",
    )
    vision_model = _model_config(
        models_raw.get("vision", {}),
        fallback_name="qwen-vision-flash",
        fallback_base="https://openrouter.ai/api/v1",
        fallback_env="VISION_MODEL_API_KEY",
        fallback_model="qwen/qwen3.5-flash-02-23",
    )

    trigger = TriggerConfig(
        followup_messages=int(trigger_raw.get("followup_messages", 6)),
        followup_ttl_seconds=int(trigger_raw.get("followup_ttl_seconds", 600)),
        followup_context_messages=int(trigger_raw.get("followup_context_messages", 8)),
        followup_reply_threshold=float(trigger_raw.get("followup_reply_threshold", 0.72)),
        followup_wait_threshold=float(trigger_raw.get("followup_wait_threshold", 0.45)),
        followup_wait_seconds=int(trigger_raw.get("followup_wait_seconds", 6)),
        followup_min_reply_cooldown=int(trigger_raw.get("followup_min_reply_cooldown", 12)),
        auto_reply_min_interval=int(trigger_raw.get("auto_reply_min_interval", 300)),
        auto_reply_chance=float(trigger_raw.get("auto_reply_chance", 0.25)),
        auto_reply_max_per_hour=int(trigger_raw.get("auto_reply_max_per_hour", 10)),
        idle_new_topic_gap_seconds=int(trigger_raw.get("idle_new_topic_gap_seconds", 900)),
        idle_new_topic_wait_seconds=int(trigger_raw.get("idle_new_topic_wait_seconds", 120)),
        long_text_chars=int(trigger_raw.get("long_text_chars", 300)),
        long_text_wait_seconds=int(trigger_raw.get("long_text_wait_seconds", 45)),
        keywords=_string_list(trigger_raw.get("keywords", [])),
    )

    return AppConfig(
        base_dir=base_dir,
        onebot=onebot,
        memory=memory,
        text_model=text_model,
        vision_model=vision_model,
        trigger=trigger,
    )


def _model_config(
    raw: dict[str, Any],
    *,
    fallback_name: str,
    fallback_base: str,
    fallback_env: str,
    fallback_model: str,
) -> ModelConfig:
    reasoning = raw.get("reasoning_effort")
    return ModelConfig(
        name=str(raw.get("name", fallback_name)),
        api_base=str(raw.get("api_base", fallback_base)).rstrip("/"),
        api_key_env=str(raw.get("api_key_env", fallback_env)),
        model=str(raw.get("model", fallback_model)),
        max_tokens=int(raw.get("max_tokens", 4096)),
        reasoning_effort=str(reasoning) if reasoning else None,
    )


def _resolve_path(value: str | Path, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return base_dir / path


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]

