#!/usr/bin/env python3
"""Dispatcher for plan_guardrail PreToolUse events."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from workflow.hook import Hook

PLAN_GUARDRAIL = Path(__file__).resolve().parents[2] / "plan_guardrail.py"


def main() -> None:
    raw_input = Hook.read_stdin()

    subprocess.run(
        [
            "python3",
            str(PLAN_GUARDRAIL),
            "--hook-input",
            json.dumps(raw_input),
            "--reason",
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()

    Hook.system_message(f"Plan Guardrail Activated")


if __name__ == "__main__":
    main()
