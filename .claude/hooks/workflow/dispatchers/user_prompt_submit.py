#!/usr/bin/env python3
"""Unified UserPromptSubmit dispatcher — routes to guardrail.py, injects reminders."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.logger import log
from workflow.reminder import EXPLORE_KICKOFF
from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"
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
    hook_event_name = raw_input.get("hook_event_name", "UserPromptSubmit")
    prompt = raw_input.get("prompt", "").strip()
    decision = get_decision(raw_input)

    if decision.startswith("block"):
        reason = (
            decision[len("block, ") :]
            if decision.startswith("block, ")
            else "Blocked by guardrail"
        )
        log("UserPromptSubmit:block", reason=reason, prompt=prompt[:80])
        Hook.advanced_block(hook_event_name, reason)
        return

    # After /implement or /plan activation, inject explore kickoff reminder
    if prompt.startswith("/implement") or prompt.startswith("/plan"):
        store = StateStore(DEFAULT_STATE_PATH)
        state = store.load()
        if state.get("workflow_active") and state.get("phase") == "explore":
            log("UserPromptSubmit:reminder", reminder=EXPLORE_KICKOFF[:100])
            Hook.send_context(hook_event_name, EXPLORE_KICKOFF)


if __name__ == "__main__":
    main()
