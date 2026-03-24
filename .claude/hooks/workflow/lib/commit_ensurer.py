import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from workflow.session_state import SessionState
from workflow.hook import Hook


def activate_commit_guard(session: SessionState, reason: str) -> None:
    """
    Ensure that the commit is made to the correct branch.
    """
    session.set_full_block(
        status="active",
        exception=[{"tool_name": "agent", "tool_value": "version-manager"}],
    )


def main() -> None:
    hook_input = Hook.read_stdin()

    if hook_input is None:
        raise ValueError("No hook input found")

    session_id = hook_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")

    session = SessionState(session_id)

    if not session.workflow_active:
        return

    activate_commit_guard(
        session, reason="Please invoke version-manager agent first to commit changes"
    )
    session.set_commit(status="pending")
