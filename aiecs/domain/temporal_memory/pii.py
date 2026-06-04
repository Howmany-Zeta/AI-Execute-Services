# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Episode body redaction before temporal memory ingest (TM-075)."""

from __future__ import annotations

import hashlib

_REDACTED_SUFFIX_TEMPLATE = "\n[redacted; body_sha256_prefix={digest}]"


def redact_episode_body(body: str, *, store_raw: bool, max_chars: int = 4000) -> str:
    """
    Apply length limits before sending episode text to Graphiti / LLM extraction.

    - ``store_raw=True``: keep text up to ``max_chars`` (truncate only).
    - ``store_raw=False``: truncate overlong bodies and append a short hash placeholder.
    """
    if max_chars < 1:
        max_chars = 1
    text = body or ""
    if len(text) <= max_chars:
        return text
    if store_raw:
        return text[:max_chars]
    truncated = text[:max_chars]
    digest = hashlib.sha256(text.encode()).hexdigest()[:16]
    return truncated + _REDACTED_SUFFIX_TEMPLATE.format(digest=digest)
