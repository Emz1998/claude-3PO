import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import os
from typing import Any

from workflow.session_state import SessionState
from workflow.models.hook_input import PostToolUseInput
from workflow.hook import Hook
from workflow.config import get as cfg

SESSION = SessionState()


def record_phase(phase: str) -> None:
    """Record phase to session if STORY_ID is set, otherwise no-op."""
    story_id = SESSION.story_id
    if not story_id:
        return
    try:
        SESSION.update_session(story_id, lambda s: s["phase"].update({"current": phase}))
    except KeyError:
        pass


def record_pre_coding_phase() -> None:
    record_phase("pre-coding")


def record_coding_phase() -> None:
    record_phase("code")


def record_recent_agent(agent_name: str) -> None:
    """Record recent agent to session if STORY_ID is set."""
    story_id = SESSION.story_id
    if not story_id:
        return
    try:
        SESSION.update_session(story_id, lambda s: s["phase"].update({"recent_agent": agent_name}))
    except KeyError:
        pass


def record_plan_file_created(tool_name: str, file_path: str) -> None:
    if tool_name != "Write":
        return
    plan_dir = str(Path(cfg("paths.plans_dir")).expanduser())
    file_path_parent_dir = str(Path(file_path).parent)
    if file_path_parent_dir == plan_dir:
        story_id = SESSION.story_id
        if story_id:
            try:
                SESSION.update_session(story_id, lambda s: s.update({"plan_file_created": True}))
            except KeyError:
                pass


def main() -> None:

    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    tool_name = hook_input.tool_name

    match tool_name:
        case "EnterPlanMode":
            record_pre_coding_phase()
        case "Skill":
            skill_name = hook_input.tool_input.skill
            if skill_name == "Code":
                record_coding_phase()
        case "Agent":
            agent_name = hook_input.tool_input.subagent_type
            record_recent_agent(agent_name)


if __name__ == "__main__":
    main()
