#!/usr/bin/env python3
"""Unified SubagentStop dispatcher — routes to recorder.py, injects reminders."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.logger import log
from workflow.reminder import get_phase_transition_reminder
from workflow.session_store import SessionStore
from workflow.config import DEFAULT_STATE_JSONL_PATH
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
    hook_event_name = raw_input.get("hook_event_name", "")
    agent_type = raw_input.get("agent_type", "unknown")
    log("Agent:completed", agent_type=agent_type)

    # Validate output schema before recording
    decision = get_decision(raw_input)
    if decision.startswith("block"):
        reason = decision[len("block, "):] if decision.startswith("block, ") else "Agent output blocked by guardrail"
        log("SubagentStop:block", agent_type=agent_type, reason=reason)
        Hook.advanced_block(hook_event_name, reason)
        return

    session_id = raw_input.get("session_id", "default")
    store = SessionStore(session_id, DEFAULT_STATE_JSONL_PATH)
    phase_before = store.load().get("phase", "")
    get_recording(raw_input)

    # After recorder advances phase, inject reminder
    phase_after = store.load().get("phase", "")
    if phase_after != phase_before:
        log("Phase:transition", prev=phase_before, next=phase_after)
    reminder_text = get_phase_transition_reminder(raw_input, store)

    if reminder_text:
        log(
            "SubagentStop:reminder", agent_type=agent_type, reminder=reminder_text[:100]
        )
        Hook.send_context(hook_event_name, reminder_text)


if __name__ == "__main__":
    main()
