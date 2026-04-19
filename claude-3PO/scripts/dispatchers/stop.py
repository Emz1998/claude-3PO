#!/usr/bin/env python3
"""Stop hook — keep the main agent running while the workflow has more to do.

Serves the Claude Code ``Stop`` event. Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id or no active workflow.
    2. Honour the ``stop_hook_active`` re-entrancy flag — if Claude Code is
       already replaying our previous block, exit cleanly to avoid an infinite
       block loop.
    3. Ask ``StopGuard`` whether stopping is OK right now. On ``"block"``, emit
       a ``{"decision": "block", "reason": ...}`` JSON payload (the Stop event's
       documented block protocol; we intentionally do NOT use ``Hook.block``'s
       ``exit 2``, which is for PreToolUse-style denials).
    4. Always finish with ``exit 0``; the JSON payload is what tells Claude
       Code to keep going.
"""

import sys
import json
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore
from handlers.guardrails.stop_guard import StopGuard
from config import Config


def main() -> None:
    """Entry point — runs once per Stop event.

    Early-exit cascade: no session_id → no active workflow → mid-block re-entry
    → otherwise consult ``StopGuard`` and emit a block-JSON payload if needed.

    Example:
        >>> main()  # doctest: +SKIP — reads JSON from stdin and exits
    """
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
