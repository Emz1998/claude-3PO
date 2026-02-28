import sys

from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.stdin import read_stdin_json  # type: ignore


def main() -> None:
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")
    if hook_event_name != "PostToolUse":
        return
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return
    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")
    if "":
        return
    print("Bash command executed")


if __name__ == "__main__":
    main()
