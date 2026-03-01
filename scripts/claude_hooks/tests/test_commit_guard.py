"""Tests for commit_guard handler."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from scripts.claude_hooks.models import Skill
from scripts.claude_hooks.handlers.commit_guard import (
    _parse_args,
    _validate_scope,
    _validate_type,
    gate,
    handle,
    VALID_TYPES,
    COMMIT_FLAG,
)


# ---------------------------------------------------------------------------
# TestParseArgs
# ---------------------------------------------------------------------------
class TestParseArgs:
    def test_none_args(self):
        tool = Skill(skill="commit", args=None)
        assert _parse_args(tool) is None

    def test_empty_args(self):
        tool = Skill(skill="commit", args="")
        assert _parse_args(tool) is None

    def test_too_few_args(self):
        tool = Skill(skill="commit", args="feat TS-001/T-001 body footer")
        assert _parse_args(tool) is None

    def test_extra_args(self):
        tool = Skill(skill="commit", args="feat TS-001/T-001 summary body footer extra")
        assert _parse_args(tool) is None

    def test_valid_args(self):
        tool = Skill(skill="commit", args='feat TS-001/T-001 "fix login bug" "detailed body" "breaking change"')
        result = _parse_args(tool)
        assert result == ["feat", "TS-001/T-001", "fix login bug", "detailed body", "breaking change"]

    def test_valid_args_single_words(self):
        tool = Skill(skill="commit", args='feat TS-001/T-001 "summary" "body" "footer"')
        result = _parse_args(tool)
        assert result == ["feat", "TS-001/T-001", "summary", "body", "footer"]

    def test_unmatched_quote(self):
        tool = Skill(skill="commit", args='feat TS-001/T-001 "unmatched body footer')
        assert _parse_args(tool) is None


# ---------------------------------------------------------------------------
# TestValidateType
# ---------------------------------------------------------------------------
class TestValidateType:
    @pytest.mark.parametrize("t", list(VALID_TYPES))
    def test_valid_types(self, t):
        assert _validate_type(t) is True

    def test_invalid_type(self):
        assert _validate_type("invalid") is False

    def test_empty_type(self):
        assert _validate_type("") is False


# ---------------------------------------------------------------------------
# TestValidateScope
# ---------------------------------------------------------------------------
class TestValidateScope:
    def test_no_flag_file(self):
        with patch.object(COMMIT_FLAG, "read", return_value=None):
            assert _validate_scope("TS-001/T-001") is False

    def test_missing_current_story(self):
        with patch.object(COMMIT_FLAG, "read", return_value={"completed_tasks": ["T-001"]}):
            assert _validate_scope("TS-001/T-001") is False

    def test_missing_completed_tasks(self):
        with patch.object(COMMIT_FLAG, "read", return_value={"current_story": "TS-001"}):
            assert _validate_scope("TS-001/T-001") is False

    def test_story_mismatch(self):
        state = {"current_story": "TS-002", "completed_tasks": ["T-001"]}
        with patch.object(COMMIT_FLAG, "read", return_value=state):
            assert _validate_scope("TS-001/T-001") is False

    def test_task_not_in_completed(self):
        state = {"current_story": "TS-001", "completed_tasks": ["T-002"]}
        with patch.object(COMMIT_FLAG, "read", return_value=state):
            assert _validate_scope("TS-001/T-001") is False

    def test_valid_scope(self):
        state = {"current_story": "TS-001", "completed_tasks": ["T-001"]}
        with patch.object(COMMIT_FLAG, "read", return_value=state):
            assert _validate_scope("TS-001/T-001") is True


# ---------------------------------------------------------------------------
# TestGate — blocks all tools except Skill:commit when flag exists
# ---------------------------------------------------------------------------
class TestGate:
    BASE_INPUT = {
        "session_id": "test-session",
        "transcript_path": "/tmp/transcript",
        "cwd": "/tmp",
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_use_id": "tu-123",
        "tool_input": {"skill": "log", "args": "task T-001 completed"},
    }

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=False)
    def test_skips_when_workflow_inactive(self, mock_gate):
        with patch.object(COMMIT_FLAG, "exists", return_value=True):
            gate(self.BASE_INPUT)  # no block

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_passes_when_no_flag(self, mock_gate):
        with patch.object(COMMIT_FLAG, "exists", return_value=False):
            gate(self.BASE_INPUT)  # no block

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_allows_commit_skill(self, mock_gate):
        inp = {**self.BASE_INPUT, "tool_input": {"skill": "commit", "args": 'feat TS-001/T-001 "summary" "body" "footer"'}}
        with patch.object(COMMIT_FLAG, "exists", return_value=True):
            gate(inp)  # no block

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_blocks_non_commit_skill(self, mock_gate):
        with patch.object(COMMIT_FLAG, "exists", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                gate(self.BASE_INPUT)
            assert exc_info.value.code == 2

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_blocks_bash_tool(self, mock_gate):
        inp = {**self.BASE_INPUT, "tool_name": "Bash", "tool_input": {"command": "ls"}}
        with patch.object(COMMIT_FLAG, "exists", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                gate(inp)
            assert exc_info.value.code == 2

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_blocks_write_tool(self, mock_gate):
        inp = {**self.BASE_INPUT, "tool_name": "Write", "tool_input": {"file_path": "/tmp/f", "content": "x"}}
        with patch.object(COMMIT_FLAG, "exists", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                gate(inp)
            assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# TestHandle
# ---------------------------------------------------------------------------
class TestHandle:
    BASE_INPUT = {
        "session_id": "test-session",
        "transcript_path": "/tmp/transcript",
        "cwd": "/tmp",
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_use_id": "tu-123",
        "tool_input": {"skill": "commit", "args": 'feat TS-001/T-001 "summary" "body" "footer"'},
    }

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=False)
    def test_gate_skip(self, mock_gate):
        handle(self.BASE_INPUT)  # should return early, no error

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_non_skill_tool(self, mock_gate):
        inp = {**self.BASE_INPUT, "tool_name": "Bash", "tool_input": {"command": "ls"}}
        handle(inp)  # should return early

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_wrong_skill(self, mock_gate):
        inp = {**self.BASE_INPUT, "tool_input": {"skill": "log", "args": "task T-001 completed"}}
        handle(inp)  # should return early

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_parse_fail(self, mock_gate):
        inp = {**self.BASE_INPUT, "tool_input": {"skill": "commit", "args": "only two"}}
        handle(inp)  # should return early

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_scope_fail(self, mock_gate):
        with patch.object(COMMIT_FLAG, "read", return_value=None):
            handle(self.BASE_INPUT)  # should return early

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    def test_type_fail(self, mock_gate):
        state = {"current_story": "TS-001", "completed_tasks": ["T-001"]}
        with patch.object(COMMIT_FLAG, "read", return_value=state):
            inp = {**self.BASE_INPUT, "tool_input": {"skill": "commit", "args": 'invalid TS-001/T-001 "summary" "body" "footer"'}}
            handle(inp)  # should return early

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    @patch("scripts.claude_hooks.handlers.commit_guard.subprocess")
    @patch("scripts.claude_hooks.handlers.commit_guard.TEMPLATE_PATH")
    def test_success_removes_task_and_deletes_flag_when_empty(self, mock_template, mock_subprocess, mock_gate):
        mock_template.read_text.return_value = "{type}({scope}): {summary}\n\n{body}\n\n{footer}"
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        state = {"current_story": "TS-001", "completed_tasks": ["T-001"]}

        with patch.object(COMMIT_FLAG, "read", return_value=state), \
             patch.object(COMMIT_FLAG, "remove_from", return_value={"current_story": "TS-001", "completed_tasks": []}) as mock_remove_from, \
             patch.object(COMMIT_FLAG, "remove") as mock_remove, \
             pytest.raises(SystemExit) as exc_info:
            handle(self.BASE_INPUT)

        assert exc_info.value.code == 0
        mock_remove_from.assert_called_once_with("completed_tasks", "T-001")
        mock_remove.assert_called_once()
        assert mock_subprocess.run.call_count == 2

    @patch("scripts.claude_hooks.handlers.commit_guard.check_workflow_gate", return_value=True)
    @patch("scripts.claude_hooks.handlers.commit_guard.subprocess")
    @patch("scripts.claude_hooks.handlers.commit_guard.TEMPLATE_PATH")
    def test_success_removes_task_but_keeps_flag_when_tasks_remain(self, mock_template, mock_subprocess, mock_gate):
        mock_template.read_text.return_value = "{type}({scope}): {summary}\n\n{body}\n\n{footer}"
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        state = {"current_story": "TS-001", "completed_tasks": ["T-001", "T-002"]}

        with patch.object(COMMIT_FLAG, "read", return_value=state), \
             patch.object(COMMIT_FLAG, "remove_from", return_value={"current_story": "TS-001", "completed_tasks": ["T-002"]}) as mock_remove_from, \
             patch.object(COMMIT_FLAG, "remove") as mock_remove, \
             pytest.raises(SystemExit) as exc_info:
            handle(self.BASE_INPUT)

        assert exc_info.value.code == 0
        mock_remove_from.assert_called_once_with("completed_tasks", "T-001")
        mock_remove.assert_not_called()
        assert mock_subprocess.run.call_count == 2


# ---------------------------------------------------------------------------
# TestCommitFlagLifecycle — integration-style with real FlagFile on tmp_path
# ---------------------------------------------------------------------------
class TestCommitFlagLifecycle:
    @pytest.fixture
    def flag(self, tmp_path):
        from scripts.claude_hooks.flag_file import FlagFile
        f = FlagFile("commit_flag")
        f._path = tmp_path / "commit_flag.json"
        return f

    def test_flag_created_on_update(self, flag):
        flag.update("current_story", "TS-012")
        assert flag.exists()

    def test_accumulates_tasks(self, flag):
        flag.update("current_story", "TS-012")
        flag.append_to("completed_tasks", "T-001")
        flag.append_to("completed_tasks", "T-002")
        state = flag.read()
        assert state["current_story"] == "TS-012"
        assert state["completed_tasks"] == ["T-001", "T-002"]

    def test_deleted_on_remove(self, flag):
        flag.update("current_story", "TS-012")
        flag.remove()
        assert not flag.exists()

    def test_read_none_when_absent(self, flag):
        assert flag.read() is None
