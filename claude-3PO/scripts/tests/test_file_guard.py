"""Tests for write-code file guard — implement blocks unlisted files, build allows any code extension."""

import pytest
from models.state import Agent
from guardrails import write_guard
from helpers import make_hook_input


class TestWriteCodeFileGuardImplement:
    """Implement workflow: write-code only allows files in plan_files_to_modify."""

    def test_listed_file_allowed(self, config, state):
        state.set("workflow_type", "implement")
        state.set_plan_files_to_modify(["src/app.py", "src/utils.py"])
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "src/app.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_unlisted_file_blocked(self, config, state):
        state.set("workflow_type", "implement")
        state.set_plan_files_to_modify(["src/app.py"])
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "src/other.py"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Files to Create/Modify" in msg

    def test_empty_file_list_blocks_all(self, config, state):
        state.set("workflow_type", "implement")
        state.set_plan_files_to_modify([])
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "src/app.py"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Files to Create/Modify" in msg


class TestWriteCodeFileGuardBuild:
    """Build workflow: write-code allows any code extension (unchanged behavior)."""

    def test_any_code_file_allowed(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "src/anything.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_non_code_file_blocked(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "readme.md"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg
