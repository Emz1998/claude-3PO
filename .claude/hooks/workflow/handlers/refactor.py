import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.config import get as cfg
from workflow.state_store import StateStore

STATE_PATH = Path(cfg("paths.workflow_state"))


def main():
    hook_input = Hook.read_stdin()
    store = StateStore(STATE_PATH)
    state = store.load()
    recent_agent = state.get("recent_agent", "")
    skill_name = hook_input.get("tool_input", {}).get("skill", "")

    if recent_agent != "TestReviewer":
        return

    if skill_name != "simplify":
        Hook.block("Invoke /simplify first to simplify the code.")

    store.set("recent_skill", "simplify")


if __name__ == "__main__":
    main()
