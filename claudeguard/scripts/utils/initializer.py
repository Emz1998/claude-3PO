#!/usr/bin/env python3
"""initializer.py — Pre-workflow initialization for /implement and /build commands.

Called via bash injection in skill .md before Claude sees the prompt.
Handles arg parsing and state initialization.

Usage:
    python3 initializer.py <workflow_type> <session_id> [args...]
    python3 initializer.py implement abc-123 SK-001
    python3 initializer.py build abc-123 --tdd build a login form
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.parser import parse_skip, parse_story_id, parse_instructions
from utils.archiver import archive_plan, archive_contracts
from utils.state_store import StateStore
from config import Config

STATE_PATH = Path(__file__).resolve().parent.parent / "state.jsonl"


# ---------------------------------------------------------------------------
# State initialization
# ---------------------------------------------------------------------------


def build_initial_state(workflow_type: str, session_id: str, args: str) -> dict:
    skip = parse_skip(args)
    tdd = "--tdd" in args
    test_mode = "--test" in args
    story_id = parse_story_id(args)
    instructions = parse_instructions(args)

    return {
        "session_id": session_id,
        "workflow_active": True,
        "status": "in_progress",
        "workflow_type": workflow_type,
        "test_mode": test_mode,
        "phases": [],
        "tdd": tdd,
        "story_id": story_id,
        "skip": skip,
        "instructions": instructions,
        "agents": [],
        "plan": {
            "file_path": None,
            "written": False,
            "revised": None,
            "reviews": [],
        },
        "tasks": [],
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
    config = Config()
    archive_plan(config)
    archive_contracts(config)

    store = StateStore(state_path, session_id=session_id)

    # Clean up stale sessions
    store.cleanup_inactive()

    story_id = parse_story_id(args)
    reset = "--reset" in args
    takeover = "--takeover" in args

    # Duplicate story guard
    if story_id:
        active = store.find_active_by_story(story_id)
        if active and not reset and not takeover:
            active_ids = [s.get("session_id") for s in active]
            raise ValueError(
                f"Story '{story_id}' already active in session(s): {active_ids}. "
                f"Use --reset to start fresh or --takeover to continue."
            )

        if active and (reset or takeover):
            store.deactivate_by_story(story_id)

    # Build initial state or copy from existing session
    if takeover and story_id:
        if active:
            copied = dict(active[-1])
            copied["session_id"] = session_id
            store.reinitialize(copied)
            return

    state = build_initial_state(workflow_type, session_id, args)
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
