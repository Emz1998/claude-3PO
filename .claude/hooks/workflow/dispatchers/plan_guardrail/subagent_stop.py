#!/usr/bin/env python3
"""Dispatcher for plan_guardrail SubagentStop events."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from workflow.hook import Hook


def main() -> None:
    raw_input = Hook.read_stdin()

    subprocess.run(
        [
            "python3",
            ".claude/hooks/workflow/plan_guardrail.py",
            "--hook-input",
            json.dumps(raw_input),
        ],
        capture_output=True,
        text=True,
    )
    # SubagentStop always allows — just records state


if __name__ == "__main__":
    main()
