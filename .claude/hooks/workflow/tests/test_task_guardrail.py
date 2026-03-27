"""Tests for task guardrail — TDD Red Phase.

Tests for:
- task_recorder.py (PostToolUse TaskCreate)
- task_list_recorder.py (PostToolUse TaskList)
- task_validator.py (SubagentStop task-manager)
- phase_guard.py task-manager prerequisite
- project_manager.py key→id rename
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_WORKFLOW_DIR = _TESTS_DIR.parent
_REPO_ROOT = _WORKFLOW_DIR.parent.parent.parent

sys.path.insert(0, str(_WORKFLOW_DIR.parent))

from workflow.guards import task_recorder, task_list_recorder, task_validator, phase_guard
from workflow.state_store import StateStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def tracker_file(tmp_dir):
    return tmp_dir / "task_tracker.jsonl"


@pytest.fixture
def snapshot_file(tmp_dir):
    return tmp_dir / "task_list_snapshot.json"


@pytest.fixture
def state_path(tmp_dir):
    path = tmp_dir / "state.json"
    path.write_text(json.dumps({"phases": [], "task_manager_completed": False}))
    return path


def task_create_payload(claude_id: str, subject: str, description: str) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "TaskCreate",
        "tool_input": {"subject": subject, "description": description},
        "tool_response": {"task": {"id": claude_id, "subject": subject}},
        "session_id": "s1",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
        "tool_use_id": "u1",
    }


def task_list_payload(tasks: list) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "TaskList",
        "tool_input": {},
        "tool_response": {"tasks": tasks},
        "session_id": "s1",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
        "tool_use_id": "u2",
    }


def subagent_stop_payload(agent_type: str = "task-manager", story_id: str = "SK-001") -> dict:
    return {
        "hook_event_name": "SubagentStop",
        "agent_type": agent_type,
        "agent_id": "a1",
        "last_assistant_message": f"Tasks created for story {story_id}.",
        "session_id": "s1",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
        "stop_hook_active": False,
        "agent_transcript_path": "x.jsonl",
    }


# ---------------------------------------------------------------------------
# test_task_recorder
# ---------------------------------------------------------------------------


class TestTaskRecorder:
    def test_records_task_create(self, tracker_file):
        payload = task_create_payload("1", "T-017: Feature importance analysis", "Perform feature importance analysis")
        decision, reason = task_recorder.record(payload, tracker_file)
        assert tracker_file.exists()
        lines = tracker_file.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["id"] == "1"
        assert entry["subject"] == "T-017: Feature importance analysis"
        assert entry["description"] == "Perform feature importance analysis"

    def test_appends_multiple_tasks(self, tracker_file):
        task_recorder.record(task_create_payload("1", "T-017: First task", "Desc 1"), tracker_file)
        task_recorder.record(task_create_payload("2", "T-018: Second task", "Desc 2"), tracker_file)
        lines = tracker_file.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == "1"
        assert json.loads(lines[1])["id"] == "2"

    def test_always_returns_allow(self, tracker_file):
        payload = task_create_payload("1", "T-017: Task", "Desc")
        decision, reason = task_recorder.record(payload, tracker_file)
        assert decision == "allow"
        assert reason == ""


# ---------------------------------------------------------------------------
# test_task_list_recorder
# ---------------------------------------------------------------------------


class TestTaskListRecorder:
    def test_records_task_list_snapshot(self, snapshot_file):
        tasks = [
            {"id": "1", "subject": "T-017: Feature", "status": "pending", "blockedBy": []},
            {"id": "2", "subject": "T-018: Model", "status": "pending", "blockedBy": ["1"]},
        ]
        decision, reason = task_list_recorder.record(task_list_payload(tasks), snapshot_file)
        assert snapshot_file.exists()
        data = json.loads(snapshot_file.read_text())
        assert data == tasks

    def test_overwrites_on_second_call(self, snapshot_file):
        tasks_v1 = [{"id": "1", "subject": "T-017: Task", "status": "pending", "blockedBy": []}]
        tasks_v2 = [
            {"id": "1", "subject": "T-017: Task", "status": "pending", "blockedBy": []},
            {"id": "2", "subject": "T-018: Task", "status": "pending", "blockedBy": []},
        ]
        task_list_recorder.record(task_list_payload(tasks_v1), snapshot_file)
        task_list_recorder.record(task_list_payload(tasks_v2), snapshot_file)
        data = json.loads(snapshot_file.read_text())
        assert len(data) == 2

    def test_always_returns_allow(self, snapshot_file):
        decision, reason = task_list_recorder.record(task_list_payload([]), snapshot_file)
        assert decision == "allow"
        assert reason == ""


# ---------------------------------------------------------------------------
# test_task_validator
# ---------------------------------------------------------------------------


PROJECT_TASKS = [
    {
        "id": "T-017",
        "title": "Feature importance analysis documented",
        "description": "Perform feature importance analysis using SHAP values",
        "blocked_by": [],
        "acceptance_criteria": ["SHAP values computed"],
        "status": "Backlog", "priority": "P1", "complexity": "M", "parent_id": "SK-001",
    },
    {
        "id": "T-018",
        "title": "Model evaluation report",
        "description": "Evaluate model performance metrics",
        "blocked_by": ["T-017"],
        "acceptance_criteria": ["Report generated"],
        "status": "Backlog", "priority": "P1", "complexity": "M", "parent_id": "SK-001",
    },
    {
        "id": "T-019",
        "title": "Deploy model to staging",
        "description": "Deploy trained model to staging environment",
        "blocked_by": [],
        "acceptance_criteria": ["Model deployed"],
        "status": "Backlog", "priority": "P2", "complexity": "L", "parent_id": "SK-001",
    },
]


def _make_valid_state(tmp_dir, tracker_file, snapshot_file):
    """Set up valid tracker + snapshot matching PROJECT_TASKS."""
    # Write task tracker (3 tasks)
    for i, pt in enumerate(PROJECT_TASKS):
        claude_id = str(i + 1)
        subject = f"{pt['id']}: {pt['title']}"
        tracker_file.parent.mkdir(parents=True, exist_ok=True)
        with tracker_file.open("a") as f:
            f.write(json.dumps({"id": claude_id, "subject": subject, "description": pt["description"]}) + "\n")

    # Write task list snapshot
    snapshot_tasks = []
    id_map = {pt["id"]: str(i + 1) for i, pt in enumerate(PROJECT_TASKS)}
    for i, pt in enumerate(PROJECT_TASKS):
        claude_id = str(i + 1)
        blocked_by = [id_map[dep] for dep in pt["blocked_by"] if dep in id_map]
        snapshot_tasks.append({
            "id": claude_id,
            "subject": f"{pt['id']}: {pt['title']}",
            "status": "pending",
            "blockedBy": blocked_by,
        })
    snapshot_file.write_text(json.dumps(snapshot_tasks))


class TestTaskValidator:
    def test_pass_all_tasks_match(self, tmp_dir, state_path):
        tracker_file = tmp_dir / "task_tracker.jsonl"
        snapshot_file = tmp_dir / "task_list_snapshot.json"
        _make_valid_state(tmp_dir, tracker_file, snapshot_file)

        payload = subagent_stop_payload("task-manager", "SK-001")
        with patch("workflow.guards.task_validator._get_project_tasks", return_value=PROJECT_TASKS):
            decision, reason = task_validator.validate(
                payload, state_path,
                tracker_path=tracker_file,
                snapshot_path=snapshot_file,
            )
        assert decision == "allow", f"Expected allow, got block: {reason}"
        # state should have task_manager_completed = True
        store = StateStore(state_path)
        state = store.load()
        assert state.get("task_manager_completed") is True

    def test_fail_missing_tasks(self, tmp_dir, state_path):
        tracker_file = tmp_dir / "task_tracker.jsonl"
        snapshot_file = tmp_dir / "task_list_snapshot.json"
        # Only create 1 of 3 tasks
        tracker_file.write_text(
            json.dumps({"id": "1", "subject": "T-017: Feature importance analysis documented", "description": "Perform feature importance analysis using SHAP values"}) + "\n"
        )
        snapshot_file.write_text(json.dumps([
            {"id": "1", "subject": "T-017: Feature importance analysis documented", "status": "pending", "blockedBy": []},
        ]))

        payload = subagent_stop_payload("task-manager", "SK-001")
        with patch("workflow.guards.task_validator._get_project_tasks", return_value=PROJECT_TASKS):
            decision, reason = task_validator.validate(
                payload, state_path,
                tracker_path=tracker_file,
                snapshot_path=snapshot_file,
            )
        assert decision == "block"
        assert "count" in reason.lower() or "missing" in reason.lower() or "3" in reason

    def test_fail_wrong_subject(self, tmp_dir, state_path):
        tracker_file = tmp_dir / "task_tracker.jsonl"
        snapshot_file = tmp_dir / "task_list_snapshot.json"
        # First task has wrong subject (doesn't start with T-017:)
        entries = [
            {"id": "1", "subject": "WRONG: Not the right task", "description": "Perform feature importance analysis using SHAP values"},
            {"id": "2", "subject": "T-018: Model evaluation report", "description": "Evaluate model performance metrics"},
            {"id": "3", "subject": "T-019: Deploy model to staging", "description": "Deploy trained model to staging environment"},
        ]
        tracker_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        snapshot_tasks = [
            {"id": "1", "subject": "WRONG: Not the right task", "status": "pending", "blockedBy": []},
            {"id": "2", "subject": "T-018: Model evaluation report", "status": "pending", "blockedBy": ["1"]},
            {"id": "3", "subject": "T-019: Deploy model to staging", "status": "pending", "blockedBy": []},
        ]
        snapshot_file.write_text(json.dumps(snapshot_tasks))

        payload = subagent_stop_payload("task-manager", "SK-001")
        with patch("workflow.guards.task_validator._get_project_tasks", return_value=PROJECT_TASKS):
            decision, reason = task_validator.validate(
                payload, state_path,
                tracker_path=tracker_file,
                snapshot_path=snapshot_file,
            )
        assert decision == "block"
        assert "T-017" in reason or "subject" in reason.lower()

    def test_fail_wrong_description(self, tmp_dir, state_path):
        tracker_file = tmp_dir / "task_tracker.jsonl"
        snapshot_file = tmp_dir / "task_list_snapshot.json"
        entries = [
            {"id": "1", "subject": "T-017: Feature importance analysis documented", "description": "COMPLETELY WRONG DESCRIPTION"},
            {"id": "2", "subject": "T-018: Model evaluation report", "description": "Evaluate model performance metrics"},
            {"id": "3", "subject": "T-019: Deploy model to staging", "description": "Deploy trained model to staging environment"},
        ]
        tracker_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        snapshot_tasks = [
            {"id": "1", "subject": "T-017: Feature importance analysis documented", "status": "pending", "blockedBy": []},
            {"id": "2", "subject": "T-018: Model evaluation report", "status": "pending", "blockedBy": ["1"]},
            {"id": "3", "subject": "T-019: Deploy model to staging", "status": "pending", "blockedBy": []},
        ]
        snapshot_file.write_text(json.dumps(snapshot_tasks))

        payload = subagent_stop_payload("task-manager", "SK-001")
        with patch("workflow.guards.task_validator._get_project_tasks", return_value=PROJECT_TASKS):
            decision, reason = task_validator.validate(
                payload, state_path,
                tracker_path=tracker_file,
                snapshot_path=snapshot_file,
            )
        assert decision == "block"
        assert "description" in reason.lower() or "T-017" in reason

    def test_fail_wrong_blocked_by(self, tmp_dir, state_path):
        tracker_file = tmp_dir / "task_tracker.jsonl"
        snapshot_file = tmp_dir / "task_list_snapshot.json"
        entries = [
            {"id": "1", "subject": "T-017: Feature importance analysis documented", "description": "Perform feature importance analysis using SHAP values"},
            {"id": "2", "subject": "T-018: Model evaluation report", "description": "Evaluate model performance metrics"},
            {"id": "3", "subject": "T-019: Deploy model to staging", "description": "Deploy trained model to staging environment"},
        ]
        tracker_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        # T-018 (id=2) should be blocked by T-017 (id=1), but we put wrong id "3"
        snapshot_tasks = [
            {"id": "1", "subject": "T-017: Feature importance analysis documented", "status": "pending", "blockedBy": []},
            {"id": "2", "subject": "T-018: Model evaluation report", "status": "pending", "blockedBy": ["3"]},  # wrong!
            {"id": "3", "subject": "T-019: Deploy model to staging", "status": "pending", "blockedBy": []},
        ]
        snapshot_file.write_text(json.dumps(snapshot_tasks))

        payload = subagent_stop_payload("task-manager", "SK-001")
        with patch("workflow.guards.task_validator._get_project_tasks", return_value=PROJECT_TASKS):
            decision, reason = task_validator.validate(
                payload, state_path,
                tracker_path=tracker_file,
                snapshot_path=snapshot_file,
            )
        assert decision == "block"
        assert "blocked" in reason.lower() or "T-018" in reason or "dependency" in reason.lower()

    def test_fail_extra_tasks(self, tmp_dir, state_path):
        tracker_file = tmp_dir / "task_tracker.jsonl"
        snapshot_file = tmp_dir / "task_list_snapshot.json"
        entries = [
            {"id": "1", "subject": "T-017: Feature importance analysis documented", "description": "Perform feature importance analysis using SHAP values"},
            {"id": "2", "subject": "T-018: Model evaluation report", "description": "Evaluate model performance metrics"},
            {"id": "3", "subject": "T-019: Deploy model to staging", "description": "Deploy trained model to staging environment"},
            {"id": "4", "subject": "T-020: Extra task", "description": "Extra"},
        ]
        tracker_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        snapshot_tasks = [{"id": str(i+1), "subject": e["subject"], "status": "pending", "blockedBy": []} for i, e in enumerate(entries)]
        snapshot_file.write_text(json.dumps(snapshot_tasks))

        payload = subagent_stop_payload("task-manager", "SK-001")
        with patch("workflow.guards.task_validator._get_project_tasks", return_value=PROJECT_TASKS):
            decision, reason = task_validator.validate(
                payload, state_path,
                tracker_path=tracker_file,
                snapshot_path=snapshot_file,
            )
        assert decision == "block"
        assert "count" in reason.lower() or "4" in reason or "3" in reason

    def test_fail_no_task_list_snapshot(self, tmp_dir, state_path):
        tracker_file = tmp_dir / "task_tracker.jsonl"
        snapshot_file = tmp_dir / "task_list_snapshot.json"  # not created
        entries = [
            {"id": "1", "subject": "T-017: Feature importance analysis documented", "description": "Perform feature importance analysis using SHAP values"},
        ]
        tracker_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        # snapshot_file does NOT exist

        payload = subagent_stop_payload("task-manager", "SK-001")
        with patch("workflow.guards.task_validator._get_project_tasks", return_value=PROJECT_TASKS):
            decision, reason = task_validator.validate(
                payload, state_path,
                tracker_path=tracker_file,
                snapshot_path=snapshot_file,
            )
        assert decision == "block"
        assert "tasklist" in reason.lower() or "task list" in reason.lower() or "snapshot" in reason.lower()

    def test_skip_non_task_manager(self, tmp_dir, state_path):
        tracker_file = tmp_dir / "task_tracker.jsonl"
        snapshot_file = tmp_dir / "task_list_snapshot.json"
        payload = subagent_stop_payload("codebase-explorer", "SK-001")
        decision, reason = task_validator.validate(
            payload, state_path,
            tracker_path=tracker_file,
            snapshot_path=snapshot_file,
        )
        assert decision == "allow"
        assert reason == ""


# ---------------------------------------------------------------------------
# test_phase_guard_task_manager_prerequisite
# ---------------------------------------------------------------------------


def make_phases_state(task_manager_completed: bool) -> dict:
    phases = [
        {"name": "explore", "status": "pending", "agents": []},
        {"name": "decision", "status": "pending", "agents": []},
        {"name": "plan", "status": "pending", "agents": []},
        {"name": "write-tests", "status": "pending", "agents": []},
        {"name": "write-code", "status": "pending", "agents": []},
        {"name": "validate", "status": "pending", "agents": []},
        {"name": "pr-create", "status": "pending", "agents": []},
    ]
    return {"phases": phases, "task_manager_completed": task_manager_completed}


class TestPhaseGuardTaskManagerPrerequisite:
    def test_explore_blocked_without_task_manager(self, tmp_dir):
        state_path = tmp_dir / "state.json"
        state_path.write_text(json.dumps(make_phases_state(task_manager_completed=False)))
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "explore", "args": ""},
            "session_id": "s1", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
            "tool_use_id": "u1",
        }
        decision, reason = phase_guard.validate(payload, state_path)
        assert decision == "block"
        assert "task-manager" in reason.lower()

    def test_explore_allowed_after_task_manager(self, tmp_dir):
        state_path = tmp_dir / "state.json"
        state_path.write_text(json.dumps(make_phases_state(task_manager_completed=True)))
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "explore", "args": ""},
            "session_id": "s1", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
            "tool_use_id": "u1",
        }
        decision, reason = phase_guard.validate(payload, state_path)
        assert decision == "allow"

    def test_non_explore_phases_unaffected(self, tmp_dir):
        """decision phase is not blocked by task_manager_completed=False (explore must be done first anyway)."""
        state_path = tmp_dir / "state.json"
        # Set explore to completed so decision can run, but task_manager_completed=False
        phases_state = make_phases_state(task_manager_completed=False)
        phases_state["phases"][0]["status"] = "completed"  # explore done
        state_path.write_text(json.dumps(phases_state))
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "decision", "args": ""},
            "session_id": "s1", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
            "tool_use_id": "u1",
        }
        decision, reason = phase_guard.validate(payload, state_path)
        # decision should be allowed (task_manager check only applies to explore)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# test_project_manager_rename
# ---------------------------------------------------------------------------


class TestProjectManagerRename:
    def test_output_has_id_not_key(self):
        """view SK-001 --tasks --json output has 'id' field, not 'key'."""
        pm_path = _REPO_ROOT / "github_project" / "project_manager.py"
        result = subprocess.run(
            [sys.executable, str(pm_path), "view", "SK-001", "--tasks", "--json"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"project_manager.py failed: {result.stderr}"
        tasks = json.loads(result.stdout)
        assert isinstance(tasks, list)
        if tasks:  # only check if there are tasks
            assert "id" in tasks[0], f"Expected 'id' field, got keys: {list(tasks[0].keys())}"
            assert "key" not in tasks[0], f"'key' field should not exist, got: {list(tasks[0].keys())}"
