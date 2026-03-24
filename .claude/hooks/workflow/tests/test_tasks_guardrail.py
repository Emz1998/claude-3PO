"""Tests for tasks-generator/guardrail.py — TDD Red Phase.

These tests verify the bugs in guardrail.py and will fail against the
current implementation. They pass once the fixes are applied.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_WORKFLOW_DIR = _TESTS_DIR.parent
_TASKS_GEN_DIR = _WORKFLOW_DIR / "tasks-generator"

sys.path.insert(0, str(_WORKFLOW_DIR.parent))
sys.path.insert(0, str(_TASKS_GEN_DIR))

import guardrail


# ---------------------------------------------------------------------------
# TestValidateMatch
# ---------------------------------------------------------------------------


class TestValidateMatch:
    def test_finds_match_when_first_task_matches(self):
        tasks = [{"title": "Task A", "description": "Desc A"}]
        raw_input = {"tool_input": {"subject": "Task A", "description": "Desc A"}}
        valid, _ = guardrail.validate_match(tasks, raw_input)
        assert valid is True

    def test_finds_match_when_match_is_not_first_task(self):
        """Bug: current code returns False on first mismatch, never checks remaining tasks."""
        tasks = [
            {"title": "Task X", "description": "Desc X"},
            {"title": "Task A", "description": "Desc A"},
        ]
        raw_input = {"tool_input": {"subject": "Task A", "description": "Desc A"}}
        valid, _ = guardrail.validate_match(tasks, raw_input)
        assert valid is True

    def test_returns_false_when_no_task_matches(self):
        tasks = [
            {"title": "Task X", "description": "Desc X"},
            {"title": "Task Y", "description": "Desc Y"},
        ]
        raw_input = {"tool_input": {"subject": "Task A", "description": "Desc A"}}
        valid, _ = guardrail.validate_match(tasks, raw_input)
        assert valid is False

    def test_returns_false_for_empty_task_list(self):
        raw_input = {"tool_input": {"subject": "Task A", "description": "Desc A"}}
        valid, _ = guardrail.validate_match([], raw_input)
        assert valid is False


# ---------------------------------------------------------------------------
# TestGetTasks
# ---------------------------------------------------------------------------


class TestGetTasks:
    def test_returns_tasks_on_success(self):
        tasks = [{"title": "T1", "description": "D1"}]
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(tasks)
        with patch("subprocess.run", return_value=mock_result):
            result = guardrail.get_tasks("SK-1")
        assert result == tasks

    def test_returns_empty_list_on_subprocess_error(self):
        """Bug: CalledProcessError propagates instead of returning []."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
            result = guardrail.get_tasks("SK-1")
        assert result == []

    def test_returns_empty_list_on_invalid_json(self):
        """Bug: json.JSONDecodeError propagates instead of returning []."""
        mock_result = MagicMock()
        mock_result.stdout = "not-valid-json"
        with patch("subprocess.run", return_value=mock_result):
            result = guardrail.get_tasks("SK-1")
        assert result == []


# ---------------------------------------------------------------------------
# TestValidateBlockedBy
# ---------------------------------------------------------------------------


class TestValidateBlockedBy:
    def test_valid_dependency_passes(self):
        tasks = [{"key": "T-1", "blocked_by": "T-2"}]
        valid, _ = guardrail.validate_blocked_by("1", "2", tasks)
        assert valid is True

    def test_wrong_dependency_fails(self):
        tasks = [{"key": "T-1", "blocked_by": "T-3"}]
        valid, _ = guardrail.validate_blocked_by("1", "2", tasks)
        assert valid is False

    def test_skips_tasks_without_blocked_by_key(self):
        """Bug: KeyError raised when task has no blocked_by field."""
        tasks = [{"key": "T-1"}]
        valid, _ = guardrail.validate_blocked_by("1", "2", tasks)
        assert valid is True

    def test_skips_non_matching_task_ids(self):
        tasks = [{"key": "T-5", "blocked_by": "T-9"}]
        valid, _ = guardrail.validate_blocked_by("1", "2", tasks)
        assert valid is True


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------


class TestMain:
    def test_uses_session_id_from_stdin(self):
        """Bug: main() hardcodes SessionState('123') instead of reading session_id from input."""
        stdin_data = {
            "session_id": "real-session-id",
            "tool_name": "TaskCreate",
            "tool_input": {"subject": "X", "description": "Y"},
        }
        with (
            patch("guardrail.Hook.read_stdin", return_value=stdin_data),
            patch("guardrail.SessionState") as mock_session_cls,
            patch("guardrail.task_create_guardrail"),
        ):
            guardrail.main()
        mock_session_cls.assert_called_once_with("real-session-id")

    def test_blocks_when_no_story_id_in_session(self):
        stdin_data = {
            "session_id": "no-story-session",
            "tool_name": "TaskCreate",
            "tool_input": {"subject": "X", "description": "Y"},
        }
        mock_session = MagicMock()
        mock_session.story_id = None
        with (
            patch("guardrail.Hook.read_stdin", return_value=stdin_data),
            patch("guardrail.SessionState", return_value=mock_session),
            patch("guardrail.Hook.block", side_effect=SystemExit(2)) as mock_block,
        ):
            with pytest.raises(SystemExit):
                guardrail.main()
        mock_block.assert_called_once()
        assert "story" in mock_block.call_args[0][0].lower()

    def test_raises_on_missing_tool_name(self):
        stdin_data = {"session_id": "sid", "tool_name": ""}
        with (
            patch("guardrail.Hook.read_stdin", return_value=stdin_data),
            patch("guardrail.SessionState"),
        ):
            with pytest.raises(ValueError, match="Tool name is required"):
                guardrail.main()
