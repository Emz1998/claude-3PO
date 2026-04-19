"""Tests for write-code file guard — implement blocks unlisted files, build allows any code extension."""

import pytest
from models.state import Agent
from handlers.guardrails import write_guard, edit_guard
from helpers import make_hook_input


class TestWriteCodeFileGuardImplement:
    """Implement workflow: write-code only allows files in plan_files_to_modify."""

    def test_listed_file_allowed(self, config, state):
        state.set("workflow_type", "implement")
        state.implement.set_plan_files_to_modify(["src/app.py", "src/utils.py"])
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "src/app.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_unlisted_file_blocked(self, config, state):
        state.set("workflow_type", "implement")
        state.implement.set_plan_files_to_modify(["src/app.py"])
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "src/other.py"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Files to Create/Modify" in msg

    def test_empty_file_list_blocks_all(self, config, state):
        state.set("workflow_type", "implement")
        state.implement.set_plan_files_to_modify([])
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


class TestE2EReportWritableInTestMode:
    """Bug #4: E2E report files must be writable/editable in every phase under --test."""

    @pytest.mark.parametrize("phase", ["strategy", "architect", "backlog", "write-code"])
    def test_e2e_specs_report_write_allowed(self, config, state, phase):
        state.set("workflow_type", "specs")
        state.set("test_mode", True)
        state.add_phase(phase)
        hook = make_hook_input("Write", {"file_path": "E2E_SPECS_TEST_REPORT.md"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    @pytest.mark.parametrize("phase", ["strategy", "architect", "backlog"])
    def test_e2e_specs_report_edit_allowed(self, config, state, phase):
        state.set("workflow_type", "specs")
        state.set("test_mode", True)
        state.add_phase(phase)
        hook = make_hook_input("Edit", {"file_path": "E2E_SPECS_TEST_REPORT.md"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_e2e_legacy_report_still_allowed(self, config, state):
        state.set("workflow_type", "specs")
        state.set("test_mode", True)
        state.add_phase("strategy")
        hook = make_hook_input("Write", {"file_path": ".claude/reports/E2E_TEST_REPORT.md"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"
