"""W10 image placeholder tests."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.adapters.llm_message import llm_message_to_blocks
from aiecs.domain.context.compression.images import replace_images_for_compaction
from aiecs.domain.context.compression.types import ImageBlock, TextBlock


def test_replace_images_for_compaction() -> None:
    messages = [
        LLMMessage(
            role="user",
            content="Please summarize",
            images=[{"source": "https://example.com/screen.png", "source_path": "/tmp/screen.png"}],
        ),
        LLMMessage(role="assistant", content="Working"),
    ]

    replaced = replace_images_for_compaction(messages)

    blocks = llm_message_to_blocks(replaced[0])
    assert not any(isinstance(block, ImageBlock) for block in blocks)
    assert any(
        isinstance(block, TextBlock) and "Image omitted from compaction" in block.text
        for block in blocks
    )
    assert replaced[1].content == "Working"
