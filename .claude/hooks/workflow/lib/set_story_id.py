"""Reset workflow state."""

import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from workflow.session_state import SessionState


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-id", type=str, required=True)
    args = parser.parse_args()
    session_id = args.session_id
    SessionState().set_session_id(session_id)
    print(f"Session ID set to {session_id}")
    sys.exit(2)


if __name__ == "__main__":
    main()
