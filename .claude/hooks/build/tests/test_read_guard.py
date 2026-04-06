"""Tests for guards/read_guard.py."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from build.guards import read_guard
from build.session_store import SessionStore


CODING_PHASES = ["write-tests", "write-code", "validate", "ci-check", "report"]
NON_ENFORCED_PHASES = ["explore", "plan", "write-plan", "review", "present-plan", "task-create"]


def make_state(phase: str, plan_file: str = None, **kwargs) -> dict:
    state = {
        "workflow_active": True,
        "workflow_type": "implement",
        "phase": phase,
        "plan": {
            "file_path": plan_file,
            "written": False,
            "review": {"iteration": 0, "scores": None, "status": None},
        },
        "docs_to_read": kwargs.get("docs_to_read", None),
    }
    if "files_written" in kwargs:
        state["files_written"] = kwargs["files_written"]
    return state


def write_state(tmp_state_file, state: dict) -> None:
    SessionStore("s", tmp_state_file).save(state)


def read_hook(file_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": file_path},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


PLAN_CONTENT = """# My Plan

## Context
Test plan.

## Files to Modify
| File | Action |
|------|--------|
| `src/app.py` | Create |
| `src/utils.py` | Edit |
| `tests/test_app.py` | Create |

## Verification
Run pytest.
"""


class TestReadGuardInactive:
    def test_read_allowed_when_workflow_inactive(self, tmp_state_file):
        tmp_state_file.write_text("")
        store = SessionStore("s", tmp_state_file)
        decision, _ = read_guard.validate(read_hook("src/app.py"), store)
        assert decision == "allow"


class TestNonEnforcedPhases:
    @pytest.mark.parametrize("phase", NON_ENFORCED_PHASES)
    def test_all_reads_allowed_in_non_enforced_phases(self, phase, tmp_state_file):
        write_state(tmp_state_file, make_state(phase))
        store = SessionStore("s", tmp_state_file)
        decision, _ = read_guard.validate(read_hook("any/file.py"), store)
        assert decision == "allow"


class TestCodingPhases:
    def test_codebase_md_always_allowed(self, tmp_state_file, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_CONTENT)
        write_state(tmp_state_file, make_state("write-code", plan_file=str(plan_file)))
        store = SessionStore("s", tmp_state_file)
        decision, _ = read_guard.validate(read_hook("CODEBASE.md"), store)
        assert decision == "allow"

    def test_claude_config_blocked(self, tmp_state_file, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_CONTENT)
        write_state(tmp_state_file, make_state("write-code", plan_file=str(plan_file)))
        store = SessionStore("s", tmp_state_file)
        decision, _ = read_guard.validate(read_hook(".claude/settings.json"), store)
        assert decision == "block"

    def test_node_modules_blocked(self, tmp_state_file, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_CONTENT)
        write_state(tmp_state_file, make_state("write-code", plan_file=str(plan_file)))
        store = SessionStore("s", tmp_state_file)
        decision, _ = read_guard.validate(read_hook("node_modules/react/index.js"), store)
        assert decision == "block"

    def test_file_in_plan_allowed(self, tmp_state_file, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_CONTENT)
        write_state(tmp_state_file, make_state("write-code", plan_file=str(plan_file)))
        store = SessionStore("s", tmp_state_file)
        decision, _ = read_guard.validate(read_hook("src/app.py"), store)
        assert decision == "allow"

    def test_file_not_in_plan_blocked(self, tmp_state_file, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_CONTENT)
        write_state(tmp_state_file, make_state("write-code", plan_file=str(plan_file)))
        store = SessionStore("s", tmp_state_file)
        decision, reason = read_guard.validate(read_hook("src/secret.py"), store)
        assert decision == "block"
        assert "plan" in reason.lower() or "listed" in reason.lower()

    def test_no_plan_file_allows_all(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code", plan_file=None))
        store = SessionStore("s", tmp_state_file)
        decision, _ = read_guard.validate(read_hook("any/file.py"), store)
        assert decision == "allow"

    def test_test_file_always_allowed_in_write_tests(self, tmp_state_file, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_CONTENT)
        write_state(tmp_state_file, make_state("write-tests", plan_file=str(plan_file)))
        store = SessionStore("s", tmp_state_file)
        decision, _ = read_guard.validate(read_hook("tests/test_other.py"), store)
        assert decision == "allow"

    def test_plan_files_cached_on_second_call(self, tmp_state_file, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_CONTENT)
        write_state(tmp_state_file, make_state("write-code", plan_file=str(plan_file)))
        store = SessionStore("s", tmp_state_file)
        # First call — parses file
        read_guard.validate(read_hook("src/app.py"), store)
        # Second call — should use cache
        read_guard.validate(read_hook("src/utils.py"), store)
        state = store.load()
        assert state.get("docs_to_read") is not None

    def test_config_files_blocked(self, tmp_state_file, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_CONTENT)
        write_state(tmp_state_file, make_state("write-code", plan_file=str(plan_file)))
        store = SessionStore("s", tmp_state_file)
        for f in ["package.json", "tsconfig.json", "pyproject.toml", ".env.example"]:
            decision, _ = read_guard.validate(read_hook(f), store)
            assert decision == "block", f"Expected {f} to be blocked"

    def test_previously_written_file_allowed(self, tmp_state_file, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_CONTENT)
        write_state(tmp_state_file, make_state(
            "write-code", plan_file=str(plan_file),
            files_written=["src/helper.py"],
        ))
        store = SessionStore("s", tmp_state_file)
        decision, _ = read_guard.validate(read_hook("src/helper.py"), store)
        assert decision == "allow"
