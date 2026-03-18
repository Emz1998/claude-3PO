import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.config import get as cfg


def release_force_stop() -> None:
    session = SessionState(Path(cfg("paths.workflow_state")))
    session.set(
        "force_stop",
        False,
    )


if __name__ == "__main__":
    release_force_stop()
