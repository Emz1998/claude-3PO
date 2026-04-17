"""Project configuration — replaces config.yaml."""

from pathlib import Path

PROJECT = "Claude-3PO"
REPO = "Emz1998/claude-3PO"
OWNER = "Emz1998"
PROJECT_NUMBER = 4

_BASE = Path(__file__).parent

DATA_PATHS = {
    "backlog": str(_BASE / "issues" / "backlog.json"),
}
