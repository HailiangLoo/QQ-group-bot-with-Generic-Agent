"""OpenAI-compatible vision caption calls."""

from __future__ import annotations

from .config import ModelConfig
from .prompts import IMAGE_CAPTION_PROMPT
import base64
import mimetypes
import requests


def caption_image_bytes(
    config: ModelConfig,
    image_bytes: bytes,
    *,
    mime_type: str = "image/png",
    instruction: str = IMAGE_CAPTION_PROMPT,
    timeout: int = 120,
) -> tuple[str, dict]:
    if not config.api_key:
        raise RuntimeError(f"Missing API key env var: {config.api_key_env}")

    data_url = "data:%s;base64,%s" % (
        mime_type,
        base64.b64encode(image_bytes).decode("ascii"),
    )
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": config.max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        f"{config.api_base}/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    text = data["choices"][0]["message"].get("content", "")
    return sanitize_caption(text), data.get("usage", {})


def sanitize_caption(text: str, *, max_chars: int = 20000) -> str:
    """Drop pathological multimodal outputs before they enter chat context."""
    cleaned = (text or "").strip()
    if len(cleaned) > max_chars:
        return "[vision_warning] 图片描述过长，已丢弃。请用更窄的问题重新看图。"
    compact = "".join(cleaned.split())
    if compact:
        unit = compact[: max(20, min(200, len(compact) // 8))]
        if unit and compact.count(unit) >= 8:
            return "[vision_warning] 图片描述疑似重复循环，已丢弃。请用更窄的问题重新看图。"
    return cleaned


def guess_mime(path: str, default: str = "image/png") -> str:
    guessed, _ = mimetypes.guess_type(path)
    return guessed or default
