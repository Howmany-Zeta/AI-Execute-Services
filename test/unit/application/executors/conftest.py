# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Fixtures for OperationExecutor unit tests."""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, Generator, List, Optional

import pytest

from aiecs.application.executors.operation_executor import OperationExecutor
from aiecs.tools import TOOL_CLASSES, TOOL_REGISTRY
from aiecs.tools.base_tool import BaseTool
from aiecs.tools.tool_executor.tool_executor import ToolExecutor
from aiecs.utils.execution_utils import ExecutionUtils


class _StubResearchTool(BaseTool):
    """Lightweight stand-in for the removed ResearchTool (executor plumbing only)."""

    description = "Stub research tool for OperationExecutor unit tests"

    def __init__(self, config: Optional[Dict[str, Any]] = None, tool_name: str = "research", **kwargs: Any) -> None:
        super().__init__(config=config or {}, tool_name=tool_name, **kwargs)

    def mill_agreement(self, cases: Any) -> Dict[str, Any]:
        if cases == "FORCE_ERROR":
            raise RuntimeError("forced research stub failure")
        if isinstance(cases, str) and len(cases) > 1024 * 1024:
            raise ValueError("input too large")
        return {"factors": ["a"], "case_count": len(cases) if cases else 0}

    def mill_difference(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"factors": [], "case_count": len(cases) if cases else 0}


@pytest.fixture(autouse=True)
def _register_stub_research_tool() -> Any:
    """Keep legacy research.* operation specs working after ResearchTool removal."""
    previous_cls = TOOL_CLASSES.get("research")
    previous_inst = TOOL_REGISTRY.pop("research", None)
    TOOL_CLASSES["research"] = _StubResearchTool
    try:
        yield
    finally:
        if previous_cls is not None:
            TOOL_CLASSES["research"] = previous_cls
        else:
            TOOL_CLASSES.pop("research", None)
        TOOL_REGISTRY.pop("research", None)
        if previous_inst is not None:
            TOOL_REGISTRY["research"] = previous_inst


@pytest.fixture
def tool_executor() -> ToolExecutor:
    return ToolExecutor(
        {
            "enable_cache": True,
            "cache_size": 50,
            "cache_ttl": 300,
            "max_workers": 2,
            "log_level": "WARNING",
            "retry_attempts": 2,
            "timeout": 10,
        }
    )


@pytest.fixture
def execution_utils() -> ExecutionUtils:
    return ExecutionUtils(cache_size=50, cache_ttl=300, retry_attempts=2, retry_backoff=0.5)


@pytest.fixture
def operation_executor(tool_executor: ToolExecutor, execution_utils: ExecutionUtils) -> OperationExecutor:
    return OperationExecutor(
        tool_executor,
        execution_utils,
        {
            "rate_limit_requests_per_second": 10,
            "batch_size": 5,
            "enable_cache": True,
        },
    )


@pytest.fixture
def sample_csv_file() -> Generator[str, None, None]:
    """Minimal CSV path used by legacy executor tests as a dummy file param."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as handle:
        handle.write("a,b\n1,2\n3,4\n")
        path = handle.name
    try:
        yield path
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.fixture
def mock_save_callback() -> Any:
    """Async-compatible save callback used by sequence-operation tests."""

    class MockSaveCallback:
        def __init__(self) -> None:
            self.calls: List[Any] = []

        async def __call__(self, user_id: str, task_id: str, step: int, result: Any) -> None:
            self.calls.append((user_id, task_id, step, result))

    return MockSaveCallback()
