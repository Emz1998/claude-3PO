"""initializer.py — Pre-workflow initialization for /plan and /implement commands.

Called via bash injection in command .md files before Claude sees the prompt.
Handles arg parsing, story conflict detection, and state initialization.

Usage:
    python3 initializer.py <workflow_type> <session_id> [args...]
    python3 initializer.py implement abc-123 SK-123 --tdd --skip-all

Exit codes:
    2 — story conflict found, session must stop (reason printed to stderr)
    (no exit) — success, returns normally
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.config import DEFAULT_STATE_JSONL_PATH, STORY_ID_PATTERN
from workflow.session_store import SessionStore


# ---------------------------------------------------------------------------
# Arg parsing (same logic as former skill_guard.py)
# ---------------------------------------------------------------------------


def parse_skip(args: str) -> list[str]:
    skip: list[str] = []
    if "--skip-explore" in args or "--skip-all" in args:
        skip.append("explore")
    if "--skip-research" in args or "--skip-all" in args:
        skip.append("research")
    return skip


def parse_story_id(args: str) -> str | None:
    m = STORY_ID_PATTERN.search(args)
    return m.group(1) if m else None


def parse_instructions(args: str) -> str:
    flags = ["--skip-explore", "--skip-research", "--skip-all", "--tdd"]
    text = STORY_ID_PATTERN.sub("", args)
    for flag in flags:
        text = text.replace(flag, "")
    return text.strip()


# ---------------------------------------------------------------------------
# Conflict check
# ---------------------------------------------------------------------------


def check_story_conflict(
    story_id: str, current_session_id: str, jsonl_path: Path = DEFAULT_STATE_JSONL_PATH
) -> None:
    """Exit 2 if another active session is implementing the same story."""
    if not story_id:
        return

    if not jsonl_path.exists():
        return

    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("session_id") == current_session_id:
            continue
        if not entry.get("workflow_active"):
            continue
        if entry.get("story_id") == story_id:
            other_sid = entry.get("session_id", "unknown")
            print(
                f"Story {story_id} is already being implemented in session {other_sid}. "
                f"Finish or stop that session before starting a new one.",
                file=sys.stderr,
            )
            sys.exit(2)


# ---------------------------------------------------------------------------
# State initialization
# ---------------------------------------------------------------------------


def build_initial_state(workflow_type: str, args: str) -> dict:
    skip = parse_skip(args)
    instructions = parse_instructions(args)
    story_id = parse_story_id(args) if workflow_type == "implement" else None
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
        "story_id": story_id,
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
        "pr_status": "pending",
        "ci_status": "pending",
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
    story_id = parse_story_id(args) if workflow_type == "implement" else None

    # Conflict check before writing state
    if story_id:
        check_story_conflict(story_id, session_id, jsonl_path)

    # Build and write initial state
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
