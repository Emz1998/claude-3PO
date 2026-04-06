#!/usr/bin/env python3
"""Unified PostToolUse dispatcher — routes to guardrail.py and recorder.py, injects reminders."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from build.hook import Hook
from build.logger import log
from build.reminder import get_post_tool_reminder
from build.session_store import SessionStore
from build.config import DEFAULT_STATE_JSONL_PATH
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
    tool_name = raw_input.get("tool_name", "")
    hook_event_name = raw_input.get("hook_event_name", "")

    log("PostToolUse:raw_input", raw_input=raw_input)

    # Skill activation goes through guardrail (blocking)
    if tool_name == "Skill":
        decision = get_decision(raw_input)
        if decision.startswith("block"):
            reason = (
                decision[len("block, ") :]
                if decision.startswith("block, ")
                else "Blocked by guardrail"
            )
            skill = raw_input.get("tool_input", {}).get("skill", "")
            log("PostToolUse:block", tool="Skill", reason=reason, skill=skill)
            Hook.system_message(f"[Guardrail] {reason}")
            return

    # Recording for Write/Edit/Bash/ExitPlanMode
    session_id = raw_input.get("session_id", "default")
    if tool_name in ("Write", "Edit", "Bash", "ExitPlanMode"):
        store_pre = SessionStore(session_id, DEFAULT_STATE_JSONL_PATH)
        phase_before = store_pre.load().get("phase", "")
        get_recording(raw_input)
        phase_after = store_pre.load().get("phase", "")
        if phase_after != phase_before:
            log("Phase:transition", prev=phase_before, next=phase_after)

    # Reminder injection (Agent reminders handled in PreToolUse)
    if tool_name != "Agent":
        store = SessionStore(session_id, DEFAULT_STATE_JSONL_PATH)
        reminder_text = get_post_tool_reminder(raw_input, store)

        if reminder_text:
            log("PostToolUse:reminder", tool=tool_name, reminder=reminder_text[:100])
            Hook.send_context(hook_event_name, reminder_text)


if __name__ == "__main__":
    main()
