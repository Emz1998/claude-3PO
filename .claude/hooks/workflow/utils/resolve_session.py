import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState


def resolve_session(raw_input: dict) -> SessionState:
    session_id = raw_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)
    return session
