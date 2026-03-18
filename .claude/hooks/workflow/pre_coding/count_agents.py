"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import StateStore
from workflow.session_state import SessionState


STATE_FILE = Path(__file__).parent / "tmp.json"


def count_explore_agents(raw_input: dict) -> None:

    agent_type = raw_input.get("tool_input", {}).get("subagent_type", "")
    if agent_type != "Explore":
        return

    tmp_state = StateStore(STATE_FILE)

    tmp_state.set("explore_agents_count", tmp_state.get("explore_agents_count", 0) + 1)


def main() -> None:
    raw_input = Hook.read_stdin()
    count_explore_agents(raw_input)


if __name__ == "__main__":
    main()
