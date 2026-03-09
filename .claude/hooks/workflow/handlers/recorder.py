import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
from typing import Any, cast

from workflow.state_store import StateStore
from workflow.models.hook_input import PreToolUseInput, PostToolUseInput, SkillTool
from workflow.hook import Hook
from workflow.config import get as cfg

STATE_PATH = Path(cfg("paths.workflow_state"))

STATE_STORE = StateStore(STATE_PATH)


def record(key: str, value: Any) -> None:
    STATE_STORE.set(key, value)


def record_pre_coding_phase() -> None:
    record("recent_phase", "Pre-Coding")


def record_coding_phase() -> None:
    record("recent_phase", "Coding")


def record_recent_agent(agent_name: str) -> None:
    record("recent_agent", agent_name)


def record_plan_file_created(tool_name: str, file_path: str) -> None:
    if tool_name != "Write":
        return
    plan_dir = str(Path(cfg("paths.plans_dir")).expanduser())
    file_path_parent_dir = str(Path(file_path).parent)
    if file_path_parent_dir == plan_dir:
        record("plan_file_created", True)


def main() -> None:

    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    tool_name = hook_input.tool_name

    match tool_name:
        case "EnterPlanMode":
            record("enter_plan_mode_triggered", True)
        case "Skill":
            skill_name = hook_input.tool_input.skill
            if skill_name == "Code":
                record_coding_phase()
        case "Agent":
            agent_name = hook_input.tool_input.subagent_type
            record_recent_agent(agent_name)


if __name__ == "__main__":
    main()
