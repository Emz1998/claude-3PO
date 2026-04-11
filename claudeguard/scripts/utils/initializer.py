#!/usr/bin/env python3
"""initializer.py — Pre-workflow initialization for /build command.

Called via bash injection in build.md before Claude sees the prompt.
Handles arg parsing and state initialization. No story IDs or conflict checks.

Usage:
    python3 initializer.py <workflow_type> <session_id> [args...]
    python3 initializer.py build abc-123 --tdd --skip-all build a login form
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constants import STORY_ID_PATTERN
from utils.state_store import StateStore

STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"


# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------


def parse_skip(args: str) -> list[str]:
    skip: list[str] = []
    if "--skip-explore" in args or "--skip-all" in args:
        skip.append("explore")
    if "--skip-research" in args or "--skip-all" in args:
        skip.append("research")
    return skip


def parse_story_id(args: str) -> str | None:
    match = re.search(STORY_ID_PATTERN, args)
    return match.group(1) if match else None


def parse_instructions(args: str) -> str:
    flags = ["--skip-explore", "--skip-research", "--skip-all", "--tdd"]
    text = re.sub(STORY_ID_PATTERN, "", args)
    for flag in flags:
        text = text.replace(flag, "")
    return text.strip()


# ---------------------------------------------------------------------------
# State initialization
# ---------------------------------------------------------------------------


def build_initial_state(workflow_type: str, session_id: str, args: str) -> dict:
    skip = parse_skip(args)
    tdd = "--tdd" in args
    story_id = parse_story_id(args)
    instructions = parse_instructions(args)

    return {
        "session_id": session_id,
        "workflow_active": True,
        "workflow_type": workflow_type,
        "phases": [],
        "tdd": tdd,
        "story_id": story_id,
        "skip": skip,
        "instructions": instructions,
        "agents": [],
        "plan": {
            "file_path": None,
            "written": False,
            "revised": False,
            "reviews": [],
        },
        "tasks": [],
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
        "ci-check": {"status": "pending", "results": []},
        "report_written": False,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def initialize(
    workflow_type: str,
    session_id: str,
    args: str,
    state_path: Path = STATE_PATH,
) -> None:
    state = build_initial_state(workflow_type, session_id, args)
    store = StateStore(state_path)
    store.reinitialize(state)


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: initializer.py <workflow_type> <session_id> [args...]",
            file=sys.stderr,
        )
        return

    workflow_type = sys.argv[1]
    session_id = sys.argv[2]
    args = " ".join(sys.argv[3:])

    initialize(workflow_type, session_id, args)


if __name__ == "__main__":
    main()
