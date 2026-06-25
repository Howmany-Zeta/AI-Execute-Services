"""Placeholder module for future OpenHarness compact parity tests."""

from __future__ import annotations

import pytest

import aiecs.domain.context.compression as compression


@pytest.mark.compression
def test_compression_package_importable() -> None:
    assert compression.AUTOCOMPACT_BUFFER_TOKENS == 13_000
    assert "read_file" in compression.COMPACTABLE_TOOLS
