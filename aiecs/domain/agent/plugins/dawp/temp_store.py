# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
temp_store: task-scoped temp file writer for dynamic DAWP documents (D2-02, §4.6).

``write_task_temp_md`` writes a dynamic ``document_content`` string to a deterministic
directory layout ``<base_dir>/aiecs_dawp/<task_id>/<uuid>.dawp.md`` so that:

- Each task has its own subdirectory (``task_id``) preventing cross-task collision.
- Each ``dawp_start`` call gets a unique filename (``uuid``).
- ``DawpPlugin.on_post_task`` can wipe the temp file (or retain it for debug) by
  following the path stored in ``DawpPendingRun.temp_document_path``.
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# Default base directory for all DAWP temp files.
# ``write_task_temp_md`` lets callers override this per-call.
_DEFAULT_BASE_DIR: Path | None = None


def _default_base() -> Path:
    """Return the default base directory (system tmpdir)."""
    if _DEFAULT_BASE_DIR is not None:
        return _DEFAULT_BASE_DIR
    return Path(tempfile.gettempdir())


def write_task_temp_md(
    content: str,
    *,
    task_id: str,
    base_dir: str | Path | None = None,
) -> Path:
    """Write *content* to a task-scoped temp ``*.dawp.md`` file and return the path.

    Directory layout::

        <base_dir>/aiecs_dawp/<task_id>/<uuid>.dawp.md

    The directory is created (with parents) if it does not exist.
    The caller is responsible for deleting the file afterwards
    (``DawpPlugin.on_post_task`` handles this unless ``retain_for_debug=True``).

    Args:
        content:  Full ``*.dawp.md`` text to write (UTF-8).
        task_id:  Identifier for the current agent task (prevents cross-task collision).
        base_dir: Override for the root temp directory.  Defaults to the system tmpdir.

    Returns:
        :class:`pathlib.Path` pointing at the newly written file.
    """
    root = Path(base_dir) if base_dir is not None else _default_base()
    task_dir = root / "aiecs_dawp" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    file_path = task_dir / f"{uuid.uuid4()}.dawp.md"
    file_path.write_text(content, encoding="utf-8")

    logger.debug(
        "temp_store: wrote dynamic DAWP document to %s (%d bytes)",
        file_path,
        len(content.encode("utf-8")),
    )
    return file_path
