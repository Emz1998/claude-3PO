"""Tests for task_created.py — TaskCreated hook matching logic.

The hook validates that task subjects match planned tasks extracted from the plan,
and that task descriptions are non-empty.
"""

import json
import subprocess
import sys
import pytest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
TASK_CREATED_SCRIPT = SCRIPTS_DIR / "dispatchers" / "task_created.py"

DEFAULT_STATE = {
    "session_id": "test-session",
    "workflow_active": True,
    "workflow_type": "build",
    "phases": [{"name": "write-tests", "status": "in_progress"}],
    "tdd": False,
    "story_id": None,
    "skip": [],
    "instructions": "",
    "agents": [],
    "plan": {"file_path": None, "written": False, "revised": False, "reviews": []},
    "tasks": ["Build authentication module", "Create user database schema", "Write API endpoints"],
    "dependencies": {"packages": [], "installed": False},
    "contracts": {"file_path": None, "names": [], "code_files": [], "written": False, "validated": False},
    "tests": {"file_paths": [], "executed": False, "reviews": [], "files_to_revise": [], "files_revised": []},
    "code_files_to_write": [],
    "code_files": {"file_paths": [], "reviews": [], "tests_to_revise": [], "tests_revised": [], "files_to_revise": [], "files_revised": []},
    "quality_check_result": None,
    "pr": {"status": "pending", "number": None},
    "ci": {"status": "pending", "results": None},
    "report_written": False,
}


def _run_hook(payload: dict, state_path: Path) -> subprocess.CompletedProcess:
    """Run task_created.py with a payload piped to stdin."""
    return subprocess.run(
        [sys.executable, str(TASK_CREATED_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        env={**__import__("os").environ, "TASK_CREATED_STATE_PATH": str(state_path)},
    )


def _task_payload(subject: str, description: str = "A valid description") -> dict:
    return {
        "hook_event_name": "TaskCreated",
        "task_subject": subject,
        "task_description": description,
        "session_id": "test-session",
    }


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    p = tmp_path / "state.jsonl"
    line = json.dumps(DEFAULT_STATE, separators=(",", ":"))
    p.write_text(line + "\n")
    return p


class TestTaskCreatedMatching:
    def test_exact_match_allowed(self, state_path):
        result = _run_hook(_task_payload("Build authentication module"), state_path)
        assert result.returncode == 0

    def test_case_insensitive_match(self, state_path):
        result = _run_hook(_task_payload("build authentication module"), state_path)
        assert result.returncode == 0

    def test_substring_match_task_in_planned(self, state_path):
        result = _run_hook(_task_payload("Build authentication"), state_path)
        assert result.returncode == 0

    def test_substring_match_planned_in_task(self, state_path):
        result = _run_hook(_task_payload("Build authentication module with OAuth integration"), state_path)
        assert result.returncode == 0

    def test_no_match_blocked(self, state_path):
        result = _run_hook(_task_payload("Deploy to production"), state_path)
        assert result.returncode == 2

    def test_empty_subject_blocked(self, state_path):
        result = _run_hook(_task_payload(""), state_path)
        assert result.returncode == 2

    def test_whitespace_only_subject_blocked(self, state_path):
        result = _run_hook(_task_payload("   "), state_path)
        assert result.returncode == 2


class TestTaskCreatedDescription:
    def test_empty_description_blocked(self, state_path):
        result = _run_hook(_task_payload("Build authentication module", ""), state_path)
        assert result.returncode == 2

    def test_whitespace_description_blocked(self, state_path):
        result = _run_hook(_task_payload("Build authentication module", "   "), state_path)
        assert result.returncode == 2

    def test_valid_description_allowed(self, state_path):
        result = _run_hook(
            _task_payload("Build authentication module", "Implement JWT-based auth"),
            state_path,
        )
        assert result.returncode == 0


class TestTaskCreatedWorkflowInactive:
    def test_inactive_workflow_allows_all(self, tmp_path):
        inactive_state = dict(DEFAULT_STATE)
        inactive_state["workflow_active"] = False
        state_path = tmp_path / "state.jsonl"
        line = json.dumps(inactive_state, separators=(",", ":"))
        state_path.write_text(line + "\n")
        result = _run_hook(_task_payload("Anything goes"), state_path)
        assert result.returncode == 0

    def test_session_mismatch_allows_all(self, state_path):
        payload = _task_payload("Anything goes")
        payload["session_id"] = "different-session"
        result = _run_hook(payload, state_path)
        assert result.returncode == 0


class TestTaskCreatedNoPlannedTasks:
    def test_no_tasks_in_state_blocks(self, tmp_path):
        state = dict(DEFAULT_STATE)
        state["tasks"] = []
        state_path = tmp_path / "state.jsonl"
        line = json.dumps(state, separators=(",", ":"))
        state_path.write_text(line + "\n")
        result = _run_hook(_task_payload("Some task"), state_path)
        assert result.returncode == 2


# ═══════════════════════════════════════════════════════════════════
# Implement workflow — project task matching + child recording
# ═══════════════════════════════════════════════════════════════════


IMPLEMENT_STATE = {
    "session_id": "test-session",
    "workflow_active": True,
    "workflow_type": "implement",
    "phases": [{"name": "create-tasks", "status": "in_progress"}],
    "tdd": False,
    "story_id": "SK-001",
    "skip": [],
    "instructions": "",
    "agents": [],
    "plan": {"file_path": None, "written": False, "revised": False, "reviews": []},
    "tasks": [],
    "project_tasks": [
        {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": []},
        {"id": "T-002", "title": "Create schema", "status": "in_progress", "subtasks": []},
    ],
    "dependencies": {"packages": [], "installed": False},
    "contracts": {"file_path": None, "names": [], "code_files": [], "written": False, "validated": False},
    "tests": {"file_paths": [], "executed": False, "reviews": [], "files_to_revise": [], "files_revised": []},
    "code_files_to_write": [],
    "code_files": {"file_paths": [], "reviews": [], "tests_to_revise": [], "tests_revised": [], "files_to_revise": [], "files_revised": []},
    "quality_check_result": None,
    "pr": {"status": "pending", "number": None},
    "ci": {"status": "pending", "results": None},
    "report_written": False,
    "plan_files_to_modify": [],
}


@pytest.fixture
def implement_state_path(tmp_path: Path) -> Path:
    p = tmp_path / "state.jsonl"
    line = json.dumps(IMPLEMENT_STATE, separators=(",", ":"))
    p.write_text(line + "\n")
    return p


class TestImplementTaskCreatedMatching:
    def test_exact_match_allowed(self, implement_state_path):
        result = _run_hook(_task_payload("Build login"), implement_state_path)
        assert result.returncode == 0

    def test_case_insensitive_match(self, implement_state_path):
        result = _run_hook(_task_payload("build login"), implement_state_path)
        assert result.returncode == 0

    def test_substring_match(self, implement_state_path):
        result = _run_hook(_task_payload("Build login with OAuth"), implement_state_path)
        assert result.returncode == 0

    def test_no_match_blocked(self, implement_state_path):
        result = _run_hook(_task_payload("Deploy to production"), implement_state_path)
        assert result.returncode == 2

    def test_records_subtask_in_state(self, implement_state_path):
        """Flat storage: the subtask is appended to ``project_tasks`` with
        ``parent_task_id`` pointing to the matched parent (T-001)."""
        from lib.state_store import StateStore
        _run_hook(_task_payload("Build login"), implement_state_path)
        state = StateStore(implement_state_path, session_id="test-session")
        ptasks = state.project_tasks
        subs = [pt for pt in ptasks if pt.get("parent_task_id") == "T-001"]
        assert len(subs) == 1
        assert subs[0]["subject"] == "Build login"


class TestImplementNoProjectTasks:
    def test_no_project_tasks_blocks(self, tmp_path):
        state = dict(IMPLEMENT_STATE)
        state["project_tasks"] = []
        state_path = tmp_path / "state.jsonl"
        line = json.dumps(state, separators=(",", ":"))
        state_path.write_text(line + "\n")
        result = _run_hook(_task_payload("Some task"), state_path)
        assert result.returncode == 2
