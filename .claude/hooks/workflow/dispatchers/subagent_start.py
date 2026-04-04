#!/usr/bin/env python3
"""SubagentStart dispatcher — injects agent-role reminders into subagent context."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.reminder import get_agent_start_reminder
from workflow.session_store import SessionStore
from workflow.config import DEFAULT_STATE_JSONL_PATH


def main() -> None:
    raw_input = Hook.read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "")
    session_id = raw_input.get("session_id", "default")
    store = SessionStore(session_id, DEFAULT_STATE_JSONL_PATH)
    reminder_text = get_agent_start_reminder(raw_input, store)

    if reminder_text:
        Hook.send_context(hook_event_name, reminder_text)


if __name__ == "__main__":
    main()
