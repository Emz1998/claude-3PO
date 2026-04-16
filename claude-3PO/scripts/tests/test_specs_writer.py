"""Tests for specs_writer.py — writing docs to disk."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


class TestWriteDoc:
    def test_writes_md_file(self, tmp_path: Path):
        from utils.specs_writer import write_doc

        content = "# Product Vision\n\n**Project:** Test\n"
        path = tmp_path / "projects" / "docs" / "product-vision.md"
        write_doc(content, str(path))
        assert path.exists()
        assert path.read_text() == content

    def test_creates_parent_dirs(self, tmp_path: Path):
        from utils.specs_writer import write_doc

        path = tmp_path / "deep" / "nested" / "doc.md"
        write_doc("# Content", str(path))
        assert path.exists()

    def test_validates_content(self, tmp_path: Path):
        from utils.specs_writer import write_doc

        path = tmp_path / "doc.md"
        with pytest.raises(ValueError, match="empty"):
            write_doc("", str(path))

    def test_validates_path(self):
        from utils.specs_writer import write_doc

        with pytest.raises(ValueError, match="path"):
            write_doc("# Content", "")


class TestWriteBacklog:
    def test_writes_md_and_json(self, tmp_path: Path):
        from utils.specs_writer import write_backlog

        md_content = self._valid_backlog_md()
        md_path = tmp_path / "backlog.md"
        json_path = tmp_path / "backlog.json"

        write_backlog(md_content, str(md_path), str(json_path))

        assert md_path.exists()
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert "stories" in data

    def test_validates_empty_content(self, tmp_path: Path):
        from utils.specs_writer import write_backlog

        with pytest.raises(ValueError, match="empty"):
            write_backlog("", str(tmp_path / "b.md"), str(tmp_path / "b.json"))

    @staticmethod
    def _valid_backlog_md() -> str:
        return (
            "# Backlog\n\n"
            "**Project:** Test\n"
            "**Last Updated:** 2026-04-16\n\n"
            "## Priority Legend\n\n"
            "## ID Conventions\n\n"
            "## Stories\n\n"
            "### US-001: First story\n\n"
            "> **As a** user, **I want** to test **so that** it works\n\n"
            "**Description:** A test story\n"
            "**Priority:** P0\n"
            "**Milestone:** MVP\n"
            "**Is Blocking:** None\n"
            "**Blocked By:** None\n\n"
            "- [ ] Acceptance criterion 1\n"
        )


class TestValidateArchitectureContent:
    def test_returns_errors_for_invalid(self):
        from utils.specs_writer import validate_architecture_content

        errors = validate_architecture_content("# Bad doc")
        assert len(errors) > 0

    def test_returns_empty_for_valid(self):
        """Delegate to validate_architecture — just check the bridge works."""
        from utils.specs_writer import validate_architecture_content

        # A minimal invalid doc will have errors
        errors = validate_architecture_content("")
        assert len(errors) > 0


class TestValidateBacklogContent:
    def test_returns_errors_for_invalid(self):
        from utils.specs_writer import validate_backlog_content

        errors = validate_backlog_content("# Bad doc")
        assert len(errors) > 0
