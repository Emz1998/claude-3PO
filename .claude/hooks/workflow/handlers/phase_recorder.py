"""PostToolUse handler — records recent_phase after pre-coding agent invocations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore
from workflow.models.hook_input import PostToolUseInput
from workflow.hook import Hook
from workflow.config import get as cfg

STATE_PATH = Path(cfg("paths.workflow_state"))
PRE_CODING_AGENTS: list[str] = cfg("agents.pre_coding")


def main() -> None:
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())

    if hook_input.tool_name != "Agent":
        return

    agent_name = hook_input.tool_input.subagent_type
    if agent_name not in PRE_CODING_AGENTS:
        return

    state = StateStore(STATE_PATH)
    state.set("recent_agent", agent_name)


if __name__ == "__main__":
    main()
