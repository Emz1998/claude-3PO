import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.stdin import read_stdin_json  # type: ignore
from workflow.hook import Hook  # type: ignore


def main() -> None:
    hook_input = read_stdin_json()
    prompt = hook_input.get("prompt", "")

    if prompt.startswith("/hook_toggler"):
        Hook.advanced_output(
            {"continue": False, "stopReason": "Hooks toggled successfully"}
        )


if __name__ == "__main__":
    main()
