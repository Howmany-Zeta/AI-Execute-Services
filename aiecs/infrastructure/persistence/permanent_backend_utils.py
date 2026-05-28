# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Shared helpers for ContextEngine permanent storage backends."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def safe_json_dumps(obj: Any) -> str:
    """Serialize to JSON, handling datetime values."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return json.dumps(obj, default=lambda o: o.isoformat() if hasattr(o, "isoformat") else str(o))


def parse_created_at(value: str | None) -> datetime:
    """Parse datetime from ISO string or return current UTC time."""
    if value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc)
