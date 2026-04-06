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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from build.config import DEFAULT_STATE_JSONL_PATH, STORY_ID_PATTERN
from build.session_store import SessionStore


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


def parse_instructions(args: str) -> str:
    flags = ["--skip-explore", "--skip-research", "--skip-all", "--tdd"]
    text = STORY_ID_PATTERN.sub("", args)
    for flag in flags:
        text = text.replace(flag, "")
    return text.strip()


# ---------------------------------------------------------------------------
# State initialization
# ---------------------------------------------------------------------------


def build_initial_state(workflow_type: str, args: str) -> dict:
    skip = parse_skip(args)
    instructions = parse_instructions(args)
    tdd = "--tdd" in args

    if "explore" in skip and "research" in skip:
        phase = "plan"
    else:
        phase = "explore"

    return {
        "workflow_active": True,
        "workflow_type": workflow_type,
        "phase": phase,
        "tdd": tdd,
        "story_id": None,
        "skip": skip,
        "instructions": instructions,
        "agents": [],
        "plan": {
            "file_path": None,
            "written": False,
            "review": {
                "iteration": 0,
                "scores": None,
                "status": None,
            },
        },
        "tasks": [],
        "tests": {
            "file_paths": [],
            "review_result": None,
            "executed": False,
        },
        "docs_to_read": None,
        "files_written": [],
        "validation_result": None,
        "code_review": {
            "iteration": 0,
            "scores": None,
            "status": None,
        },
        "report_written": False,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def initialize(
    workflow_type: str,
    session_id: str,
    args: str,
    jsonl_path: Path = DEFAULT_STATE_JSONL_PATH,
) -> None:
    state = build_initial_state(workflow_type, args)
    store = SessionStore(session_id, jsonl_path)
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
