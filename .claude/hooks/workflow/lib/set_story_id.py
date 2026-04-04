"""Set story ID on a session."""

import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from workflow.session_store import SessionStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", type=str, required=True)
    parser.add_argument("--story-id", type=str, required=True)
    args = parser.parse_args()
    store = SessionStore(args.session_id)
    store.set("story_id", args.story_id)
    print(f"Story ID set to {args.story_id}")
    sys.exit(0)


if __name__ == "__main__":
    main()
