"""Tests for ProjectPaths — session/sprint path builder."""

from pathlib import Path
from unittest.mock import patch

import pytest

from workflow.paths import ProjectPaths, SESSION_DIRS


@pytest.fixture
def paths():
    return ProjectPaths(sprint_id="sprint-1", session_id="abc123")


class TestProjectPaths:
    @patch("workflow.paths.cfg", return_value="project")
    def test_base_path(self, mock_cfg, paths):
        assert paths.base_path == Path("project")

    @patch("workflow.paths.cfg", return_value="project")
    def test_sprints_path(self, mock_cfg, paths):
        assert paths.sprints_path == Path("project/sprints")

    @patch("workflow.paths.cfg", return_value="project")
    def test_current_sprint_path(self, mock_cfg, paths):
        assert paths.current_sprint_path == Path("project/sprints/sprint-1")

    @patch("workflow.paths.cfg", return_value="project")
    def test_sessions_path(self, mock_cfg, paths):
        assert paths.sessions_path == Path("project/sprints/sprint-1/sessions")

    def test_current_session_dir_valid(self):
        p = ProjectPaths(sprint_id="s1", session_id="sess1")
        # All valid session dirs should not raise
        for d in SESSION_DIRS:
            result = p.current_session_dir(d)
            assert d in str(result)

    def test_current_session_dir_invalid(self):
        p = ProjectPaths(sprint_id="s1", session_id="sess1")
        with pytest.raises(ValueError, match="Invalid session directory"):
            p.current_session_dir("invalid_dir")
