#!/usr/bin/env python3
"""Unified PreToolUse dispatcher — routes to guardrail.py and recorder.py, injects reminders."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.logger import log
from workflow.reminder import get_post_tool_reminder
from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"
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
    decision = get_decision(raw_input)

    tool_name = raw_input.get("tool_name", "")

    if decision.startswith("block"):
        reason = (
            decision[len("block, ") :]
            if decision.startswith("block, ")
            else "Blocked by guardrail"
        )
        tool_input = raw_input.get("tool_input", {})
        attempted = {}
        if tool_name == "Agent":
            attempted["agent_type"] = tool_input.get("subagent_type", "")
            attempted["background"] = tool_input.get("run_in_background", False)
        elif tool_name in ("Write", "Edit"):
            attempted["file"] = tool_input.get("file_path", "")
        elif tool_name == "Bash":
            attempted["command"] = tool_input.get("command", "")[:100]
        elif tool_name == "Skill":
            attempted["skill"] = tool_input.get("skill", "")
        log("PreToolUse:block", tool=tool_name, reason=reason, **attempted)
        Hook.advanced_block(hook_event_name, reason)
        return

    # Record agent launch (after guardrail allows)
    if tool_name == "Agent":
        agent_type = raw_input.get("tool_input", {}).get("subagent_type", "general-purpose")
        log("Agent:trigger", agent_type=agent_type)
        get_recording(raw_input)

        # Inject remaining agents reminder (reads state after recorder wrote it)
        store = StateStore(DEFAULT_STATE_PATH)
        reminder_text = get_post_tool_reminder(raw_input, store)
        if reminder_text:
            Hook.send_context(hook_event_name, reminder_text)


if __name__ == "__main__":
    main()
