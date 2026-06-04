"""Shared fixtures for document tool and orchestrator unit tests."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def document_parser_config() -> dict:
    return {
        "max_file_size": 10 * 1024 * 1024,
        "timeout": 10,
        "max_pages": 100,
        "enable_cloud_storage": False,
    }


@pytest.fixture
def ai_orchestrator_config() -> dict:
    return {
        "max_chunk_size": 2000,
        "max_concurrent_requests": 2,
        "default_temperature": 0.1,
        "max_tokens": 1000,
        "timeout": 30,
    }


@pytest.fixture
def temp_dir():
    path = Path(tempfile.mkdtemp(prefix="aiecs_docs_test_"))
    yield path
    shutil.rmtree(path, ignore_errors=True)
