#!/usr/bin/env python3
"""PreToolUse hook — dispatches to the appropriate guardrail based on tool_name."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from guardrails import TOOL_GUARDS
from utils.hook import Hook
from utils.state_store import StateStore
from config import Config


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(Path(__file__).resolve().parent / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    guard = TOOL_GUARDS.get(tool_name)
    if not guard:
        sys.exit(0)

    config = Config()

    decision, message = guard(hook_input, config, state)

    if decision == "block":
        Hook.advanced_block("PreToolUse", message)
    else:
        Hook.system_message(message)


if __name__ == "__main__":
    main()
