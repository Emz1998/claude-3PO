"""PostToolUse handler — records recent_agent after pre-coding agent invocations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.models.hook_input import PostToolUseInput
from workflow.hook import Hook
from workflow.config import get as cfg
from workflow.workflow_log import log

PRE_CODING_AGENTS: list[str] = cfg("agents.pre_coding")


def main() -> None:
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())

    if hook_input.tool_name != "Agent":
        return

    agent_name = hook_input.tool_input.subagent_type
    if agent_name not in PRE_CODING_AGENTS:
        return

    session = SessionState()
    story_id = session.story_id
    if not story_id:
        return

    try:
        log("PhaseRecorder", "Recorded", f"Recent agent recorded: {agent_name}")
        session.update_session(
            story_id, lambda s: s["phase"].update({"recent_agent": agent_name})
        )
    except KeyError:
        pass


if __name__ == "__main__":
    main()
