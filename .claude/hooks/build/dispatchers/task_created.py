#!/usr/bin/env python3
"""Unified TaskCreated dispatcher — routes to guardrail.py and recorder.py."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from build.hook import Hook
from build.logger import log

GUARDRAIL = str(Path(__file__).parent.parent / "guardrail.py")
RECORDER = str(Path(__file__).parent.parent / "recorder.py")


def get_decision(raw_input: dict[str, Any]) -> str:
    result = subprocess.run(
        ["python3", GUARDRAIL, "--hook-input", json.dumps(raw_input), "--reason"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_recording(raw_input: dict[str, Any]) -> str:
    result = subprocess.run(
        ["python3", RECORDER, "--hook-input", json.dumps(raw_input)],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    raw_input = Hook.read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "TaskCreated")
    decision = get_decision(raw_input)

    if decision.startswith("block"):
        reason = decision[len("block, "):] if decision.startswith("block, ") else "Task blocked by guardrail"
        subject = raw_input.get("task_subject", "")
        log("TaskCreated:block", reason=reason, subject=subject)
        Hook.advanced_block(hook_event_name, reason)
        return

    get_recording(raw_input)


if __name__ == "__main__":
    main()
