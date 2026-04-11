#!/usr/bin/env python3
"""Stop hook — prevents the main agent from stopping if workflow isn't done."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.hook import Hook
from utils.state_store import StateStore
from utils.runners import check_phases, check_tests, check_ci
from config import Config


def main() -> None:
    hook_input = Hook.read_stdin()

    state = StateStore(Path(__file__).resolve().parent / "state.json")
    if not state.get("workflow_active"):
        sys.exit(0)
    if hook_input.get("session_id") != state.get("session_id"):
        sys.exit(0)

    if hook_input.get("stop_hook_active"):
        sys.exit(0)

    config = Config()

    failures: list[str] = []

    checks = [
        lambda: check_phases(config, state),
        lambda: check_tests(state),
        lambda: check_ci(state),
    ]

    for check in checks:
        try:
            check()
        except SystemExit as e:
            if e.code != 0:
                failures.append(str(e))

    if failures:
        output = {
            "decision": "block",
            "reason": "\n".join(failures),
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
