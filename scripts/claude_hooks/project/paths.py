#!/usr/bin/env python3
"""PreToolUse guardrail for /implement workflow subagent ordering.

Ensures subagents are triggered in the correct order:
1. codebase-explorer (requires TODO_READ state)
2. planning-specialist (requires EXPLORER_DONE state)
3. plan-consultant (requires PLANNER_DONE state)
4. Then coding workflow based on TDD/TA/DEFAULT mode

Blocks subagent execution (exit 2) if triggered out of order.
Uses task owner from roadmap.json to determine expected engineer subagent.
"""

import sys
from pathlib import Path
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Literal, get_args


from scripts.claude_hooks.utils.hook import Hook  # type: ignore
from scripts.claude_hooks.utils.state_store import StateStore  # type: ignore
from scripts.claude_hooks.sprint.sprint import Sprint  # type: ignore
from scripts.claude_hooks.utils.file_manager import FileManager  # type: ignore


BASE_DIR = Path("project/sprints/")

SessionDirs = Literal[
    "exploration",
    "planning",
    "review",
    "testing",
    "troubleshooting",
    "reports",
]

SESSION_DIRS = get_args(SessionDirs)


class Session:
    """Session class."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


@dataclass
class ProjectPaths:
    """Phase transition guard."""

    sprint_id: str
    session_id: str

    def __post_init__(self) -> None:
        self.base_path = Path("project")

    @property
    def base_path(self) -> Path:
        return Path("project")

    @base_path.setter
    def base_path(self, path: Path) -> None:
        self.path = path

    @property
    def sprints_path(self) -> Path:
        return self.base_path / "sprints"

    @sprints_path.setter
    def sprints_path(self, path: Path) -> None:
        self.path = path

    @property
    def current_sprint_path(self) -> Path:
        return self.sprints_path / self.sprint_id

    @property
    def sessions_path(self) -> Path:
        return self.current_sprint_path / "sessions"

    @sessions_path.setter
    def sessions_path(self, path: Path) -> None:
        self.path = path

    @property
    def current_session_path(self) -> Path:
        return (
            self.sessions_path
            / f"session_{datetime.now().strftime('%m%d%y')}_{self.session_id}"
        )

    def current_session_dir(self, dir_name: SessionDirs) -> Path:
        if dir_name not in SESSION_DIRS:
            raise ValueError(f"Invalid session directory: {dir_name}")
        return self.current_session_path / dir_name
