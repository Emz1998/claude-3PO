#!/usr/bin/env python3
"""SessionStart:clear dispatcher — handles phase advancement after ExitPlanMode clears context."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from build.hook import Hook
from build.logger import log
from build.recorder import advance_after_plan_approval
from build.reminder import get_session_start_clear_reminder
from build.session_store import SessionStore
from build.config import DEFAULT_STATE_JSONL_PATH


def main() -> None:
    raw_input = Hook.read_stdin()
    source = raw_input.get("source", "")

    # Clean up inactive sessions on every session start
    SessionStore.cleanup_inactive(DEFAULT_STATE_JSONL_PATH)

    if source != "clear":
        return

    session_id = raw_input.get("session_id", "default")
    store = SessionStore(session_id, DEFAULT_STATE_JSONL_PATH)
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
