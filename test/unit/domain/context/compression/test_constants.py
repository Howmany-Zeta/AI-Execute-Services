"""Compression constants parity with OpenHarness defaults."""

from __future__ import annotations

from aiecs.domain.context.compression import constants as cc


def test_autocompact_buffer_tokens() -> None:
    assert cc.AUTOCOMPACT_BUFFER_TOKENS == 13_000


def test_compactable_tools_match_openharness() -> None:
    expected = {
        "read_file",
        "bash",
        "grep",
        "glob",
        "web_search",
        "web_fetch",
        "edit_file",
        "write_file",
    }
    assert cc.COMPACTABLE_TOOLS == frozenset(expected)


def test_context_collapse_limits() -> None:
    assert cc.CONTEXT_COLLAPSE_TEXT_CHAR_LIMIT == 2_400
    assert cc.CONTEXT_COLLAPSE_HEAD_CHARS == 900
    assert cc.CONTEXT_COLLAPSE_TAIL_CHARS == 500


def test_session_memory_limits() -> None:
    assert cc.SESSION_MEMORY_KEEP_RECENT == 12
    assert cc.SESSION_MEMORY_MAX_LINES == 48
    assert cc.SESSION_MEMORY_MAX_CHARS == 4_000


def test_autocompact_failure_and_token_padding() -> None:
    assert cc.MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES == 3
    assert cc.TOKEN_ESTIMATION_PADDING == 4 / 3


def test_ptl_retry_marker() -> None:
    assert cc.PTL_RETRY_MARKER == (
        "[earlier conversation truncated for compaction retry]"
    )


def test_constants_module_allows_local_override(monkeypatch) -> None:
    monkeypatch.setattr(cc, "AUTOCOMPACT_BUFFER_TOKENS", 10_000)
    assert cc.AUTOCOMPACT_BUFFER_TOKENS == 10_000
