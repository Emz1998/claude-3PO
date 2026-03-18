"""Reset workflow state."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from workflow.session_state import SessionState


def main() -> None:
    default_state = SessionState().default_state()
    SessionState().reset(default_state)
    print("Workflow state reset")
    sys.exit(2)


if __name__ == "__main__":
    main()
