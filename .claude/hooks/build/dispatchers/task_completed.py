#!/usr/bin/env python3
"""Unified TaskCompleted dispatcher — routes to guardrail.py."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from build.hook import Hook
from build.logger import log

GUARDRAIL = str(Path(__file__).parent.parent / "guardrail.py")


def get_decision(raw_input: dict[str, Any]) -> str:
    result = subprocess.run(
        ["python3", GUARDRAIL, "--hook-input", json.dumps(raw_input), "--reason"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    raw_input = Hook.read_stdin()
    decision = get_decision(raw_input)

    if decision.startswith("block"):
        reason = decision[len("block, "):] if decision.startswith("block, ") else "Task completion blocked by guardrail"
        subject = raw_input.get("task_subject", "")
        log("TaskCompleted:block", reason=reason, subject=subject)
        Hook.advanced_block("TaskCompleted", reason)
        return

    subject = raw_input.get("task_subject", "")
    log("TaskCompleted:allow", subject=subject)


if __name__ == "__main__":
    main()
