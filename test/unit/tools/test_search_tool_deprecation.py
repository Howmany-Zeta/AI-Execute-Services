"""P0-01: SearchTool deprecation revoked (M-D.5 Phase 0)."""

from __future__ import annotations

import subprocess
import sys


def test_search_tool_import_emits_no_deprecation_warning() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::DeprecationWarning",
            "-c",
            "from aiecs.tools.search_tool import SearchTool",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
