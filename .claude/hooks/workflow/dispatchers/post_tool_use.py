#!/usr/bin/env python3
"""Unified PostToolUse dispatcher — routes to guardrail.py."""

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
    hook_event_name = raw_input.get("hook_event_name", "")
    decision = get_decision(raw_input)

    # PostToolUse: block output goes to stderr as system message
    if decision.startswith("block"):
        reason = decision[len("block, "):] if decision.startswith("block, ") else "Blocked by guardrail"
        Hook.system_message(f"[Guardrail] {reason}")
    # JSON passthrough for additionalContext (ExitPlanMode)
    elif decision.startswith("{"):
        print(decision)


if __name__ == "__main__":
    main()
