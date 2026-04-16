#!/usr/bin/env python3
"""PostToolUse hook — records tool results and runs resolvers."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore
from utils.recorder import Recorder
from utils.resolver import resolve
from config import Config


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(SCRIPTS_DIR / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    config = Config()

    try:
        Recorder(state).record(hook_input, config)
    except ValueError as e:
        Hook.block(str(e))

    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))

    sys.exit(0)


if __name__ == "__main__":
    main()
