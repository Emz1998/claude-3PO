"""Tests for project_manager.config — guards against data-path drift."""

from __future__ import annotations

from pathlib import Path

from project_manager import config


class TestDataPaths:
    """Ensure configured data paths resolve to files that actually exist."""

    def test_backlog_path_exists(self) -> None:
        # Regression guard: backlog was migrated from issues/backlog.json to
        # project.json; config.DATA_PATHS must keep pointing at real data.
        backlog_path = Path(config.DATA_PATHS["backlog"])
        assert backlog_path.is_file(), (
            f"config.DATA_PATHS['backlog'] points to {backlog_path}, "
            "which does not exist — did the backlog file get renamed?"
        )
