"""Reset workflow state."""

import sys
from pathlib import Path
import argparse
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from workflow.session_store import SessionStore


PATTERN = r"^(SK|TS|US|BG)-\d{3}$"


def parse_story_id(story_id: str) -> str:
    if re.match(PATTERN, story_id):
        return story_id
    print(f"Invalid story ID: {story_id}")
    sys.exit(2)


def initialize_session(
    store: SessionStore, story_id: str, session_id: str, workflow_type: str
) -> None:
    store.reinitialize({
        "workflow_active": True,
        "workflow_type": workflow_type,
        "story_id": story_id,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", type=str, required=True)
    parser.add_argument("--story-id", type=str, required=True)
    parser.add_argument("--dry-run", action="store_true", required=False, default=False)
    parser.add_argument(
        "--workflow-type", type=str, required=False, default="implement"
    )
    args = parser.parse_args()
    session_id = args.session_id
    story_id = parse_story_id(args.story_id)
    dry_run = args.dry_run

    store = SessionStore(session_id)
    initialize_session(store, story_id, session_id, args.workflow_type)

    if dry_run:
        print("Dry run mode enabled")
        print(f"Session ID set to {session_id}")
        print(f"Story ID set to {story_id}")

        sys.exit(2)

    print(f"Session ID set to {session_id}")
    print(f"Story ID set to {story_id}")
    sys.exit(0)


if __name__ == "__main__":
    main()
