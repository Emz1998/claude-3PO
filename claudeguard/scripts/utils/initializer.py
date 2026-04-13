#!/usr/bin/env python3
"""initializer.py — Pre-workflow initialization for /implement and /build commands.

Called via bash injection in skill .md before Claude sees the prompt.
Handles arg parsing and state initialization.

Usage:
    python3 initializer.py <workflow_type> <session_id> [args...]
    python3 initializer.py implement abc-123 SK-001
    python3 initializer.py build abc-123 --tdd build a login form
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constants import STORY_ID_PATTERN
from utils.state_store import StateStore
from config import Config

STATE_PATH = Path(__file__).resolve().parent.parent / "state.jsonl"


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
    flags = [
        "--skip-explore", "--skip-research", "--skip-all", "--tdd",
        "--reset", "--takeover",
    ]
    text = re.sub(STORY_ID_PATTERN, "", args)
    for flag in flags:
        text = text.replace(flag, "")
    return text.strip()


# ---------------------------------------------------------------------------
# Plan archiving
# ---------------------------------------------------------------------------


def parse_frontmatter(content: str) -> dict[str, str]:
    """Extract frontmatter key-value pairs from markdown."""
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip()
    return fm


def archive_plan(config: Config) -> None:
    """Archive existing latest-plan.md before starting a new workflow."""
    plan_path = Path(config.plan_file_path)
    if not plan_path.exists():
        return

    content = plan_path.read_text()
    fm = parse_frontmatter(content)
    session_id = fm.get("session_id", "unknown")
    date = datetime.now().strftime("%Y-%m-%d")

    archive_dir = Path(config.plan_archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"plan_{date}_{session_id}.md"
    shutil.copy2(plan_path, archive_dir / archive_name)
    plan_path.unlink()


def archive_contracts(config: Config) -> None:
    """Archive existing latest-contracts.md before starting a new workflow."""
    contracts_path = Path(config.contracts_file_path)
    if not contracts_path.exists():
        return

    date = datetime.now().strftime("%Y-%m-%d")

    archive_dir = Path(config.contracts_archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"contracts_{date}.md"
    shutil.copy2(contracts_path, archive_dir / archive_name)
    contracts_path.unlink()


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

    # Clean up stale sessions
    StateStore.cleanup_inactive(state_path)

    story_id = parse_story_id(args)
    reset = "--reset" in args
    takeover = "--takeover" in args

    # Duplicate story guard
    if story_id:
        active = StateStore.find_active_by_story(state_path, story_id)
        if active and not reset and not takeover:
            active_ids = [s.get("session_id") for s in active]
            raise ValueError(
                f"Story '{story_id}' already active in session(s): {active_ids}. "
                f"Use --reset to start fresh or --takeover to continue."
            )

        if active and (reset or takeover):
            StateStore.deactivate_by_story(state_path, story_id)

    # Build initial state or copy from existing session
    if takeover and story_id:
        # Copy state from the latest active session (before we deactivated them)
        # We already have the active list from before deactivation
        if active:
            copied = dict(active[-1])  # latest session
            copied["session_id"] = session_id
            store = StateStore(state_path, session_id=session_id)
            store.reinitialize(copied)
            return

    state = build_initial_state(workflow_type, session_id, args)
    store = StateStore(state_path, session_id=session_id)
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
