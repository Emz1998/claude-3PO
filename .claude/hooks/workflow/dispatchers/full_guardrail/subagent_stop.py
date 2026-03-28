import sys
import subprocess
from pathlib import Path
import json
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook


def get_decision(raw_input: dict[str, Any]) -> str:
    return subprocess.run(
        [
            "python3",
            ".claude/hooks/workflow/guardrail.py",
            "--hook-input",
            json.dumps(raw_input),
            "--reason",
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    raw_input = Hook.read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "")
    decision = get_decision(raw_input)

    if decision == "block":
        Hook.advanced_block(hook_event_name, "Blocked by guardrail")


if __name__ == "__main__":
    main()
