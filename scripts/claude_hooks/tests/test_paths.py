"""Tests for paths.py — ProjectPaths without dead setters."""

import pytest
from pathlib import Path


def test_project_paths_creates():
    from scripts.claude_hooks.paths import ProjectPaths

    p = ProjectPaths(sprint_id="SPRINT-001", session_id="abc-123")
    assert p.sprint_id == "SPRINT-001"
    assert p.session_id == "abc-123"


def test_base_path():
    from scripts.claude_hooks.paths import ProjectPaths

    p = ProjectPaths(sprint_id="SPRINT-001", session_id="abc")
    assert p.base_path == Path("project")


def test_sprints_path():
    from scripts.claude_hooks.paths import ProjectPaths

    p = ProjectPaths(sprint_id="SPRINT-001", session_id="abc")
    assert p.sprints_path == Path("project/sprints")


def test_current_sprint_path():
    from scripts.claude_hooks.paths import ProjectPaths

    p = ProjectPaths(sprint_id="SPRINT-001", session_id="abc")
    assert p.current_sprint_path == Path("project/sprints/SPRINT-001")


def test_sessions_path():
    from scripts.claude_hooks.paths import ProjectPaths

    p = ProjectPaths(sprint_id="SPRINT-001", session_id="abc")
    assert p.sessions_path == Path("project/sprints/SPRINT-001/sessions")


def test_current_session_path_contains_session_id():
    from scripts.claude_hooks.paths import ProjectPaths

    p = ProjectPaths(sprint_id="SPRINT-001", session_id="abc")
    path = p.current_session_path
    assert "abc" in str(path)
    assert "session_" in str(path)


def test_current_session_dir_valid():
    from scripts.claude_hooks.paths import ProjectPaths

    p = ProjectPaths(sprint_id="SPRINT-001", session_id="abc")
    d = p.current_session_dir("exploration")
    assert d.name == "exploration"


def test_current_session_dir_invalid_raises():
    from scripts.claude_hooks.paths import ProjectPaths

    p = ProjectPaths(sprint_id="SPRINT-001", session_id="abc")
    with pytest.raises(ValueError):
        p.current_session_dir("invalid_dir")


def test_no_dead_setters():
    """ProjectPaths should not have mutable setters that do nothing useful."""
    from scripts.claude_hooks.paths import ProjectPaths

    p = ProjectPaths(sprint_id="SPRINT-001", session_id="abc")
    # These should be read-only properties, not settable
    with pytest.raises(AttributeError):
        p.base_path = Path("/other")
    with pytest.raises(AttributeError):
        p.sprints_path = Path("/other")
    with pytest.raises(AttributeError):
        p.sessions_path = Path("/other")
