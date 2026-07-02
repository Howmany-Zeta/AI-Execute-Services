# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""CitationUrlGate — URL format and dangling ref check (A-4)."""

from __future__ import annotations

import json
import re
from typing import Any, Union
from urllib.parse import urlparse

from aiecs.domain.agent.models import AgentGoal

from .models import GateScore

_URL_PATTERN = re.compile(r"https?://[^\s\)\]>\"']+", re.IGNORECASE)
_MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")


def _extract_text(*, result: dict[str, Any], work_snapshot: dict[str, Any]) -> str:
    parts: list[str] = []
    for source in (work_snapshot, result):
        for key in ("text", "output", "final_response", "content"):
            value = source.get(key)
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(parts) if parts else json.dumps(result, default=str)


def _is_valid_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class CitationUrlGate:
    """
    Deterministic citation URL validation gate (reference impl).

    **Reference-only:** when the deliverable contains no URLs and no markdown
    links, this gate vacuously passes (score 100). That is intentional for
    contract tests but must NOT be treated as “citations verified” in production.
    """

    kind: str = "citation_url_gate"
    criterion_id: str = "criterion_citation_urls"

    def score(
        self,
        *,
        goal: Union[AgentGoal, dict[str, Any], None],
        result: dict[str, Any],
        work_snapshot: dict[str, Any],
    ) -> GateScore:
        text = _extract_text(result=result, work_snapshot=work_snapshot)
        issues: list[str] = []
        urls = _URL_PATTERN.findall(text)
        invalid = [url for url in urls if not _is_valid_url(url)]
        if invalid:
            issues.extend(f"Invalid URL format: {url}" for url in invalid[:5])

        dangling: list[str] = []
        for _label, href in _MARKDOWN_LINK.findall(text):
            href = href.strip()
            if not href or href in {"#", "TODO", "TBD", "http://", "https://"}:
                dangling.append(href or "(empty)")
            elif href.startswith(("http://", "https://")) and not _is_valid_url(href):
                dangling.append(href)

        if dangling:
            issues.extend(f"Dangling citation ref: {ref}" for ref in dangling[:5])

        if not urls and not _MARKDOWN_LINK.search(text):
            return GateScore(kind=self.kind, score=100.0, issues=[], passed=True, critical=False)

        penalty = len(invalid) * 25 + len(dangling) * 20
        score = max(0.0, 100.0 - penalty)
        passed = score >= 85.0 and not issues
        return GateScore(
            kind=self.kind,
            score=score,
            issues=issues,
            passed=passed,
            critical=bool(invalid),
        )
