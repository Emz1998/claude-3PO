#!/usr/bin/env python3
"""Stop hook — prevents the main agent from stopping if workflow isn't done."""

import sys
import json
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore
from guardrails.stop_guard import StopGuard
from config import Config


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(SCRIPTS_DIR / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    if hook_input.get("stop_hook_active"):
        sys.exit(0)

    config = Config()
    decision, message = StopGuard(config, state).validate()

    if decision == "block":
        output = {"decision": "block", "reason": message}
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
