"""Project configuration — replaces config.yaml."""

from pathlib import Path

PROJECT = "Avaris AI"
REPO = "Emz1998/avaris-ai"
OWNER = "Emz1998"
PROJECT_NUMBER = 4

_BASE = Path(__file__).parent

DATA_PATHS = {
    "project_data": str(_BASE / "project_data.json"),
    "sprint": str(_BASE / "issues" / "sprint.json"),
    "stories": str(_BASE / "issues" / "stories.json"),
}
