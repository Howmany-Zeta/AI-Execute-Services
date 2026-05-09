# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Resolve GCP service-account JSON paths per Vertex client without mutating ``os.environ``.

Each LLM client can use its own JSON key file while sharing the same process.
"""

from __future__ import annotations

import os
from typing import Any, Optional

_CLOUD_PLATFORM_SCOPE = ("https://www.googleapis.com/auth/cloud-platform",)


def _first_existing_json_path(*candidates: str) -> Optional[str]:
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def resolve_credentials_json_path(specific_path: str = "", fallback_path: str = "") -> Optional[str]:
    """Return the first existing JSON path: *specific_path* then *fallback_path*."""
    return _first_existing_json_path(specific_path, fallback_path)


def load_optional_service_account_credentials(
    *,
    specific_path: str = "",
    fallback_path: str = "",
) -> Optional[Any]:
    """Load explicit credentials from a JSON key file, or ``None`` for Application Default Credentials.

    Resolution order: per-client *specific_path*, then global *fallback_path* (typically
    ``Settings.google_application_credentials`` / ``GOOGLE_APPLICATION_CREDENTIALS``).
    Callers must validate that configured paths exist when the user set them explicitly
    (see each client).
    """
    path = resolve_credentials_json_path(specific_path, fallback_path)
    if not path:
        return None
    try:
        from google.oauth2 import service_account
    except ImportError as exc:
        raise ImportError("google-auth is required to load GCP credentials from a JSON file") from exc

    return service_account.Credentials.from_service_account_file(path, scopes=_CLOUD_PLATFORM_SCOPE)
