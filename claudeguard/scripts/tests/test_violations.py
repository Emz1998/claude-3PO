"""Tests for violations logger and async prompt summary."""

import json
import pytest
from pathlib import Path
from lib.violations import log_violation, resolve_pending_summaries, VIOLATIONS_PATH


@pytest.fixture
def violations_path(tmp_path: Path, monkeypatch) -> Path:
    p = tmp_path / "violations.md"
    monkeypatch.setattr("lib.violations.VIOLATIONS_PATH", p)
    return p


class TestLogViolation:
    def test_creates_file_with_header(self, violations_path):
        log_violation(
            session_id="sess-1",
            workflow_type="build",
            story_id=None,
            prompt_summary="build a login",
            phase="explore",
            tool="Write",
            action="test.py",
            reason="File write not allowed",
        )
        content = violations_path.read_text()
        assert "| Timestamp" in content  # header
        assert "| sess-1" in content
        assert "| build" in content
        assert "| N/A" in content  # story_id None -> N/A
        assert "| build a login" in content
        assert "| explore" in content
        assert "| Write" in content
        assert "| test.py" in content

    def test_appends_to_existing(self, violations_path):
        log_violation("s1", "build", None, "task 1", "explore", "Write", "a.py", "reason 1")
        log_violation("s1", "build", None, "task 1", "plan", "Bash", "rm -rf", "reason 2")
        lines = violations_path.read_text().strip().splitlines()
        # header + separator + 2 data rows
        assert len(lines) == 4

    def test_implement_shows_story_id(self, violations_path):
        log_violation("s1", "implement", "SK-001", None, "explore", "Write", "a.py", "reason")
        content = violations_path.read_text()
        assert "| SK-001" in content
        assert "| N/A" in content  # prompt_summary None -> N/A

    def test_pending_summary(self, violations_path):
        log_violation("s1", "build", None, None, "explore", "Write", "a.py", "reason")
        content = violations_path.read_text()
        assert "| Pending..." in content

    def test_pipes_in_reason_escaped(self, violations_path):
        log_violation("s1", "build", None, "task", "explore", "Write", "a.py", "not | allowed")
        content = violations_path.read_text()
        # Pipe in reason should not break table
        assert "not \\| allowed" in content


class TestResolvePendingSummaries:
    def test_replaces_pending_with_summary(self, violations_path):
        log_violation("s1", "build", None, None, "explore", "Write", "a.py", "reason 1")
        log_violation("s1", "build", None, None, "plan", "Bash", "cmd", "reason 2")

        resolve_pending_summaries(violations_path, "s1", "build a login form")

        content = violations_path.read_text()
        assert "Pending..." not in content
        assert "build a login form" in content

    def test_only_resolves_matching_session(self, violations_path):
        log_violation("s1", "build", None, None, "explore", "Write", "a.py", "reason")
        log_violation("s2", "build", None, None, "plan", "Bash", "cmd", "reason")

        resolve_pending_summaries(violations_path, "s1", "my summary")

        content = violations_path.read_text()
        lines = content.strip().splitlines()
        # s1 row should have summary, s2 should still be Pending...
        assert "| my summary" in lines[2]
        assert "| Pending..." in lines[3]

    def test_no_file_does_nothing(self, violations_path):
        # Should not raise
        resolve_pending_summaries(violations_path, "s1", "summary")
