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

    raw_input = Hook.read_stdin()

    command = raw_input.get("tool_input", {}).get("command", None)
    if command is None:
        raise ValueError("No command found")

    if not any(command.startswith(cmd) for cmd in COMMIT_COMMANDS):
        Hook.block(
            f"Invalid bash command: {command}. You can only use the following commands: {COMMIT_COMMANDS}"
        )
        return

    session.set("commit_command", command)


if __name__ == "__main__":
    main()
