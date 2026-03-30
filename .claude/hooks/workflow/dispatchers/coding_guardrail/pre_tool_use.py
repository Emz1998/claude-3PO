#!/usr/bin/env python3
"""Dispatcher for coding_guardrail PreToolUse events."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from workflow.hook import Hook


def main() -> None:
    raw_input = Hook.read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "PreToolUse")
    result = subprocess.run(
        [
            "python3",
            ".claude/hooks/workflow/coding_guardrail.py",
            "--hook-input",
            json.dumps(raw_input),
            "--reason",
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()

    if result.startswith("block"):
        reason = (
            result.split(", ", 1)[-1]
            if ", " in result
            else "Blocked by coding guardrail"
        )
        Hook.advanced_block(hook_event_name, reason)


if __name__ == "__main__":
    main()
