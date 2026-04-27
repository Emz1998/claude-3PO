#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from project_manager.manager import ProjectManager  # type: ignore


def init_state(session_id: str, workflow_type: str, tdd: bool, story_id: str) -> dict:

    return {
        "session_id": session_id,
        "workflow_active": True,
        "workflow_type": workflow_type,
        "status": "in_progress",
        "tdd": tdd,
        "story_id": story_id,
        "file_paths": [],
        "reviews": {
            "plan": [],
            "tests": [],
        },
        "qa_check": None,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:

    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_type", type=str)
    parser.add_argument("session_id", type=str)
    args = parser.parse_args()

    init_state(args.workflow_type, args.session_id, tdd=False, story_id="")


if __name__ == "__main__":
    main()
