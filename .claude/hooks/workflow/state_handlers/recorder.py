import sys
from pathlib import Path
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import os
from typing import Any, Literal

from workflow.session_state import SessionState
from workflow.models.hook_input import PostToolUseInput
from workflow.hook import Hook
from workflow.config import get as cfg
from workflow.utils.pr_manager import get_pr_number
from workflow.constants.constants import REVIEWER_AGENTS
from workflow.state_handlers.release_full_block import release_full_block

SESSION = SessionState(cfg("paths.workflow_state"))
PHASES = cfg("phases.workflow")


def parse_dry_run(skill_name: str) -> str:
    dry_run = skill_name.startswith("dry-run:")
    if not dry_run:
        return skill_name
    parsed_skill_name = skill_name.replace("dry-run:", "")
    return parsed_skill_name


def record_agent(agent_name: str) -> None:
    SESSION.set("agent", {"current": None, "previous": agent_name})


def record_phase(skill_name: str) -> None:
    if skill_name in PHASES:
        SESSION.set("phase", {"current": None, "previous": skill_name})
        return


def record_skill(skill_name: str) -> None:
    skill_name = parse_dry_run(skill_name)
    record_phase(skill_name)
    SESSION.set("skill", {"current": None, "previous": skill_name})


def record_command(command: str) -> None:
    SESSION.set("commands", {"current": None, "recent": command})
    if "gh pr create" in command:
        pr_number = get_pr_number()
        if pr_number:
            record_pr_status("created", pr_number)


def record_written_file(file_path: str) -> None:
    SESSION.set("written_files", {"current": None, "recent": file_path})


def record_edited_file(file_path: str) -> None:
    SESSION.set("edited_files", {"current": None, "recent": file_path})


def record_pr_status(pr_status: str, pr_number: int) -> None:
    SESSION.set("pr", {"status": pr_status, "number": pr_number})


def main() -> None:
    is_workflow_active = SESSION.workflow_active
    if not is_workflow_active:
        return

    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    tool_name = hook_input.tool_name
    match tool_name:
        case "Bash":
            record_command(hook_input.tool_input.command)
        case "Skill":
            record_skill(hook_input.tool_input.skill)
        case "Agent":
            record_agent(hook_input.tool_input.subagent_type)
        case "Write":
            record_written_file(hook_input.tool_input.file_path)
        case "Edit":
            record_edited_file(hook_input.tool_input.file_path)
        case "ExitPlanMode":
            record_phase("pre-coding")


if __name__ == "__main__":
    main()
