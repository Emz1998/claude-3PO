#!/usr/bin/env python3
"""SubagentStart dispatcher — injects agent-role reminders into subagent context."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.reminder import get_agent_start_reminder
from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"


def main() -> None:
    raw_input = Hook.read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "")
    store = StateStore(DEFAULT_STATE_PATH)
    reminder_text = get_agent_start_reminder(raw_input, store)

    if reminder_text:
        Hook.send_context(hook_event_name, reminder_text)


if __name__ == "__main__":
    main()
