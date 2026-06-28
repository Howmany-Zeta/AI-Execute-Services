# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""M2+ CompressionPolicy and O2 gate primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import AUTOCOMPACT_BUFFER_TOKENS
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tokens import (
    get_autocompact_threshold as _get_autocompact_threshold,
    should_compress_messages,
)
from aiecs.domain.context.compression.types import TruncationMode


@dataclass
class CompressionPolicy:
    """Runtime compression policy for HybridAgent tool loop (ADR-007 / O1)."""

    enabled: bool = True
    context_window_tokens: int = 200_000
    buffer_tokens: int = AUTOCOMPACT_BUFFER_TOKENS
    auto_compact_threshold_tokens: int | None = None
    max_consecutive_failures: int = 3
    preserve_recent: int = 12
    chain: tuple[str, ...] = ("microcompact", "collapse", "session_memory", "llm")
    summary_role: Literal["user", "system"] = "user"
    summary_chunk_size: int | None = None
    truncation_mode: TruncationMode = TruncationMode.EARLIER_PLACEHOLDER


def get_autocompact_threshold(policy: CompressionPolicy) -> int:
    """O2: token threshold for proactive auto-compact from policy."""
    return _get_autocompact_threshold(
        context_window_tokens=policy.context_window_tokens,
        buffer_tokens=policy.buffer_tokens,
        auto_compact_threshold_tokens=policy.auto_compact_threshold_tokens,
    )


def should_compress(
    messages: Sequence[LLMMessage],
    policy: CompressionPolicy,
    *,
    force: bool = False,
    state: AutoCompactState | None = None,
) -> bool:
    """O2: return True when messages should be compacted under policy."""
    if force:
        return True
    if not policy.enabled:
        return False
    if state is not None and state.consecutive_failures >= policy.max_consecutive_failures:
        return False
    return should_compress_messages(
        messages,
        context_window_tokens=policy.context_window_tokens,
        buffer_tokens=policy.buffer_tokens,
        auto_compact_threshold_tokens=policy.auto_compact_threshold_tokens,
        force=False,
        enabled=True,
    )


LEGACY_STRATEGY_CHAINS: dict[str, tuple[str, ...]] = {
    "truncate": ("microcompact",),
    "summarize": ("microcompact", "llm"),
    "semantic": ("microcompact",),
    "hybrid": ("microcompact", "collapse", "llm"),
}


def resolve_compact_chain(
    policy: CompressionPolicy,
    strategy: str | tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """Resolve effective compact chain from policy defaults and optional override."""
    if strategy is None:
        return policy.chain
    if isinstance(strategy, tuple):
        return strategy
    normalized = str(strategy).strip().lower()
    if normalized in LEGACY_STRATEGY_CHAINS:
        return LEGACY_STRATEGY_CHAINS[normalized]
    return policy.chain


def policy_with_chain(
    policy: CompressionPolicy,
    chain: tuple[str, ...],
) -> CompressionPolicy:
    """Return a copy of *policy* with *chain* replaced."""
    from dataclasses import replace

    return replace(policy, chain=chain)
