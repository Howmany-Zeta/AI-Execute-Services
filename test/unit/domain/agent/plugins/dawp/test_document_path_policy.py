"""Tests for static document_path allowlist (dawp_audit_v2 §3)."""

from __future__ import annotations

import pytest

from aiecs.domain.agent.plugins.dawp.document_path_policy import (
    configure_document_path_policy,
    validate_static_document_path,
)


@pytest.mark.unit
class TestDocumentPathPolicy:
    def test_exact_configured_file_allowed(self, tmp_path) -> None:
        doc = tmp_path / "wf.dawp.md"
        doc.write_text("---\nname: x\n---\n", encoding="utf-8")
        state: dict = {}
        configure_document_path_policy(state, {"document_path": str(doc)})
        resolved, reason = validate_static_document_path(str(doc), state)
        assert reason is None
        assert resolved == doc.resolve()

    def test_under_allowed_root(self, tmp_path) -> None:
        root = tmp_path / "workflows"
        root.mkdir()
        doc = root / "extra.dawp.md"
        doc.write_text("x", encoding="utf-8")
        state: dict = {}
        configure_document_path_policy(state, {"allowed_document_roots": [str(root)]})
        resolved, reason = validate_static_document_path(str(doc), state)
        assert reason is None
        assert resolved == doc.resolve()

    def test_outside_roots_rejected(self, tmp_path) -> None:
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "secret.dawp.md"
        outside.write_text("x", encoding="utf-8")
        state: dict = {}
        configure_document_path_policy(state, {"allowed_document_roots": [str(allowed)]})
        resolved, reason = validate_static_document_path(str(outside), state)
        assert resolved is None
        assert reason is not None
        assert "not under allowed" in reason

    def test_disabled_when_no_roots_configured(self, tmp_path) -> None:
        doc = tmp_path / "any.dawp.md"
        doc.write_text("x", encoding="utf-8")
        state: dict = {}
        configure_document_path_policy(state, {})
        resolved, reason = validate_static_document_path(str(doc), state)
        assert resolved is None
        assert "disabled" in (reason or "")
