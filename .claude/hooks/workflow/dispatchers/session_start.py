#!/usr/bin/env python3
"""SessionStart:clear dispatcher — handles phase advancement after ExitPlanMode clears context."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.logger import log
from workflow.recorder import advance_after_plan_approval
from workflow.reminder import get_session_start_clear_reminder
from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"


def main() -> None:
    raw_input = Hook.read_stdin()
    source = raw_input.get("source", "")

    if source != "clear":
        return

    store = StateStore(DEFAULT_STATE_PATH)
    state = store.load()

    if not state.get("workflow_active"):
        return

    phase = state.get("phase", "")
    if phase != "present-plan":
        return

    next_phase = advance_after_plan_approval(store)

    if next_phase:
        log("Phase:transition", prev="present-plan", next=next_phase, trigger="SessionStart:clear")

    reminder_text = get_session_start_clear_reminder(store)
    if reminder_text:
        log("SessionStart:reminder", reminder=reminder_text[:100])
        Hook.send_context("SessionStart", reminder_text)


if __name__ == "__main__":
    main()
