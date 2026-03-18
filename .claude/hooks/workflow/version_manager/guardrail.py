import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.state_handlers.release_full_block import release_full_block


COMMIT_COMMANDS = ["git commit", "git add", "git push"]


def main() -> None:
    session = SessionState()
    if not session.workflow_active:
        return

    if session.commit_status != "committed":
        Hook.block("Please commit changes task first ")
        return

    release_full_block(input_tool_name="agent", input_tool_value="version-manager")


if __name__ == "__main__":
    main()
