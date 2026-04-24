"""Image caption cache helpers."""

from __future__ import annotations

from collections.abc import Callable

from .live_memory import LiveMemory, hash_instruction, sha256_bytes

Captioner = Callable[[bytes], tuple[str, dict]]


class ImageCaptionCache:
    def __init__(self, memory: LiveMemory, instruction: str, model_name: str):
        self.memory = memory
        self.instruction = instruction
        self.instruction_hash = hash_instruction(instruction)
        self.model_name = model_name

    def get_or_create(self, image_bytes: bytes, captioner: Captioner) -> tuple[str, str, bool]:
        sha = sha256_bytes(image_bytes)
        cached = self.memory.get_image_caption(sha, self.instruction_hash)
        if cached is not None:
            return sha, cached, True

        caption, usage = captioner(image_bytes)
        self.memory.upsert_image_caption(
            sha256=sha,
            instruction_hash=self.instruction_hash,
            caption=caption,
            model=self.model_name,
            usage=usage,
        )
        return sha, caption, False

