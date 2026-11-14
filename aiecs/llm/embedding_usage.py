# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Stash embedding token counts from the inner client. Callers commit elsewhere."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

last_embedding_input_tokens: ContextVar[Optional[int]] = ContextVar(
    "aiecs_last_embedding_input_tokens",
    default=None,
)


def stash_embedding_input_tokens(count: Optional[int]) -> None:
    last_embedding_input_tokens.set(count)


def take_embedding_input_tokens() -> Optional[int]:
    value = last_embedding_input_tokens.get()
    last_embedding_input_tokens.set(None)
    return value
