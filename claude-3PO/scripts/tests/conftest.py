import sys
import json
from pathlib import Path

import pytest

# Add scripts/ and tests/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.state_store import StateStore
from config import Config


DEFAULT_STATE: dict = {
    "session_id": "test-session",
    "workflow_active": True,
    "status": "in_progress",
    "workflow_type": "implement",
    "phases": [],
    "tdd": False,
    "story_id": "TEST-001",
    "skip": [],
    "instructions": "",
    "agents": [],
    "plan": {
        "file_path": None,
        "written": False,
        "revised": None,
        "reviews": [],
    },
    "tasks": [],
    "project_tasks": [],
    "dependencies": {"packages": [], "installed": False},
    "contracts": {
        "file_path": None,
        "names": [],
        "code_files": [],
        "written": False,
        "validated": False,
    },
    "tests": {
        "file_paths": [],
        "executed": False,
        "reviews": [],
        "files_to_revise": [],
        "files_revised": [],
    },
    "code_files_to_write": [],
    "code_files": {
        "file_paths": [],
        "reviews": [],
        "tests_to_revise": [],
        "tests_revised": [],
        "files_to_revise": [],
        "files_revised": [],
    },
    "quality_check_result": None,
    "pr": {"status": "pending", "number": None},
    "ci": {"status": "pending", "results": None},
    "report_written": False,
    "plan_files_to_modify": [],
}

SESSION_ID = "test-session"


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    p = tmp_path / "state.jsonl"
    # Write as JSONL: one line per session
    line = json.dumps(DEFAULT_STATE, separators=(",", ":"))
    p.write_text(line + "\n")
    return p


@pytest.fixture
def state(state_path: Path) -> StateStore:
    return StateStore(state_path, session_id=SESSION_ID)


@pytest.fixture
def config() -> Config:
    return Config()
