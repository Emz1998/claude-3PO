"""Shared fixtures for workflow module tests."""

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Add tests dir to path so helpers.py is importable
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def tmp_state_file(tmp_path):
    """Create a temporary JSON state file."""
    state_file = tmp_path / "state.json"
    state_file.write_text("{}")
    return state_file


@pytest.fixture
def mock_config():
    """Patch workflow.config.get to return test values."""
    config_data = {
        "paths.base": "project",
        "paths.sprints": "project/sprints",
        "paths.workflow_state": ".claude/hooks/workflow/state.json",
        "paths.validation_log": ".claude/hooks/workflow/validation.log",
        "paths.plans_dir": "~/.claude/plans",
        "paths.templates_reminders": ".claude/hooks/workflow/templates/reminders",
        "agents.pre_coding": ["Explore", "Plan", "PlanReviewer"],
        "agents.test": ["TestEngineer", "TestReviewer"],
        "agents.code": ["CodeReviewer"],
        "agents": {
            "pre_coding": ["Explore", "Plan", "PlanReviewer"],
            "test": ["TestEngineer", "TestReviewer"],
            "code": ["CodeReviewer"],
        },
        "phases.workflow": ["explore", "plan", "code", "validate", "push"],
        "session_dirs": ["exploration", "planning", "review", "testing", "troubleshooting", "reports"],
        "validation.iteration_loop": 3,
        "validation.confidence_score": 70,
        "validation.quality_score": 70,
        "validation.ci_max_iterations": 2,
        "reminders.map": [
            {"event": "PostToolUse", "tool": "EnterPlanMode", "agent": None, "template": "pre_coding_phase.md"},
            {"event": "PostToolUse", "tool": "Agent", "agent": "Plan", "template": "plan_review.md"},
        ],
    }

    def fake_get(dotted_key: str, default: Any = None) -> Any:
        return config_data.get(dotted_key, default)

    with patch("workflow.config.get", side_effect=fake_get) as mock:
        yield mock


@pytest.fixture
def mock_state_store(tmp_path):
    """In-memory state dict backed by a temp file."""
    state_file = tmp_path / "state.json"
    state_file.write_text("{}")
    return state_file


@pytest.fixture
def mock_session_state(tmp_path):
    """SessionState backed by a temp file with a pre-created session."""
    from workflow.session_state import SessionState

    state_file = tmp_path / "state.json"
    session_data = SessionState.default_implement_session("SK-TEST", "test-uuid")
    initial = {"sessions": {"SK-TEST": session_data}, "workflow_active": True}
    state_file.write_text(json.dumps(initial))
    return SessionState(state_path=state_file)


@pytest.fixture
def story_id_env(monkeypatch):
    """Set STORY_ID=SK-TEST in the environment."""
    monkeypatch.setenv("STORY_ID", "SK-TEST")
