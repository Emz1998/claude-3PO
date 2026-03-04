"""ProjectPaths — session/sprint path builder. Read-only properties."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, get_args

SessionDirs = Literal[
    "exploration",
    "planning",
    "review",
    "testing",
    "troubleshooting",
    "reports",
]

SESSION_DIRS = get_args(SessionDirs)


@dataclass(frozen=False)
class ProjectPaths:
    sprint_id: str
    session_id: str
    file_name: str = "state.json"

    @property
    def base_path(self) -> Path:
        return Path("project")

    @property
    def sprints_path(self) -> Path:
        return self.base_path / "sprints"

    @property
    def current_sprint_path(self) -> Path:
        return self.sprints_path / self.sprint_id

    @property
    def sessions_path(self) -> Path:
        return self.current_sprint_path / "sessions"

    @property
    def current_session_path(self) -> Path:
        return (
            self.sessions_path
            / f"session_{datetime.now().strftime('%m%d%y')}_{self.session_id}"
            / self.file_name
        )

    def current_session_dir(self, dir_name: SessionDirs) -> Path:
        if dir_name not in SESSION_DIRS:
            raise ValueError(f"Invalid session directory: {dir_name}")
        return self.current_session_path / dir_name
