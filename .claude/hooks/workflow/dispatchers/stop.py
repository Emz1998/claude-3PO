#!/usr/bin/env python3
"""Unified Stop dispatcher — routes to guardrail.py."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.logger import log


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
    decision = get_decision(raw_input)

    if decision.startswith("block"):
        reason = decision[len("block, "):] if decision.startswith("block, ") else "Workflow incomplete"
        log("Stop:block", reason=reason)
        Hook.block(reason)


if __name__ == "__main__":
    main()
