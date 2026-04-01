#!/usr/bin/env python3
"""Unified UserPromptSubmit dispatcher — routes to guardrail.py."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook


def get_decision(raw_input: dict[str, Any]) -> str:
    result = subprocess.run(
        [
            "python3",
            str(Path(__file__).parent.parent / "guardrail.py"),
            "--hook-input",
            json.dumps(raw_input),
            "--reason",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    raw_input = Hook.read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "UserPromptSubmit")
    decision = get_decision(raw_input)

    if decision.startswith("block"):
        reason = decision[len("block, "):] if decision.startswith("block, ") else "Blocked by guardrail"
        Hook.advanced_block(hook_event_name, reason)


if __name__ == "__main__":
    main()
