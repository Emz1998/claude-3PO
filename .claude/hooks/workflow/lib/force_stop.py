import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from workflow.session_state import SessionState
from workflow.hook import Hook

def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)
    if not session.workflow_active:
        return

    force_stop = session.get("force_stop", {}).get("status", "inactive") == "active"
    if force_stop:
        Hook.advanced_output(
            {
                "continue": False,
                "stopReason": session.get("force_stop", {}).get(
                    "reason", "Force stopped"
                ),
                "systemMessage": f"""Claude was forced to stop due to:
                {session.get("force_stop", {}).get(
                    "reason", "Force stopped"
                )}""",
            }
        )
        return


if __name__ == "__main__":
    main()
