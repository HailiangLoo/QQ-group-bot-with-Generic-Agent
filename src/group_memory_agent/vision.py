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
    return text.strip(), data.get("usage", {})


def guess_mime(path: str, default: str = "image/png") -> str:
    guessed, _ = mimetypes.guess_type(path)
    return guessed or default

