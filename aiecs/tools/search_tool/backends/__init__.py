# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Grounding search backend protocol and shared call/result types."""

from .protocol import (
    BackendRawResult,
    GroundingSearchBackend,
    SearchCallParams,
)
from .registry import (
    BUILTIN_BACKEND_ALIASES,
    GroundingBackendRegistry,
    normalize_backend_name,
    normalize_provider_chain,
)
from .credentials import CredentialResolver, log_fallback_warning_once, reset_fallback_warning_state_for_tests
from .google_cse import GoogleCseBackend
from .gemini_grounding import GeminiGroundingBackend
from .grok_grounding import GrokGroundingBackend

__all__ = [
    "BUILTIN_BACKEND_ALIASES",
    "BackendRawResult",
    "CredentialResolver",
    "GeminiGroundingBackend",
    "GoogleCseBackend",
    "GrokGroundingBackend",
    "GroundingSearchBackend",
    "GroundingBackendRegistry",
    "SearchCallParams",
    "log_fallback_warning_once",
    "normalize_backend_name",
    "normalize_provider_chain",
    "reset_fallback_warning_state_for_tests",
]
