"""skill_guard.py — Intercepts /plan and /implement skill invocations.

Handles PostToolUse(Skill) and UserPromptSubmit events.
Activates workflow state with flat state model.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore

STORY_ID_PATTERN = re.compile(r'\b([A-Z]{2,}-\d+)\b')


def _parse_skill_and_args(hook_input: dict) -> tuple[str, str]:
    """Extract skill name and args from PostToolUse(Skill) or UserPromptSubmit."""
    event = hook_input.get("hook_event_name", "")
    if event == "UserPromptSubmit":
        prompt = hook_input.get("prompt", "").strip()
        if not prompt.startswith("/"):
            return "", ""
        parts = prompt[1:].split(" ", 1)
        skill = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        return skill, args
    elif event == "PostToolUse":
        tool_input = hook_input.get("tool_input", {})
        return tool_input.get("skill", ""), tool_input.get("args", "")
    return "", ""


def _parse_skip_args(args: str) -> dict:
    return {
        "skip_explore": "--skip-explore" in args or "--skip-all" in args,
        "skip_research": "--skip-research" in args or "--skip-all" in args,
    }


def _parse_instructions(args: str) -> str:
    flags = ["--skip-explore", "--skip-research", "--skip-all", "--tdd"]
    # Also remove story IDs
    text = STORY_ID_PATTERN.sub("", args)
    for flag in flags:
        text = text.replace(flag, "")
    return text.strip()


def _parse_story_id(args: str) -> str | None:
    m = STORY_ID_PATTERN.search(args)
    return m.group(1) if m else None


def _initial_state(workflow_type: str, args: str) -> dict:
    skip = _parse_skip_args(args)
    instructions = _parse_instructions(args)
    story_id = _parse_story_id(args) if workflow_type == "implement" else None
    tdd = "--tdd" in args

    # Determine starting phase
    if skip["skip_explore"] and skip["skip_research"]:
        phase = "plan"
    else:
        phase = "explore"

    return {
        "workflow_active": True,
        "workflow_type": workflow_type,
        "phase": phase,
        "tdd": tdd,
        "story_id": story_id,
        "skip_explore": skip["skip_explore"],
        "skip_research": skip["skip_research"],
        "instructions": instructions,
        "agents": [],
        "plan_file": None,
        "plan_written": False,
        "plan_review_iteration": 0,
        "plan_review_scores": None,
        "plan_review_status": None,
        "tasks_created": 0,
        "test_files_created": [],
        "test_review_result": None,
        "test_run_executed": False,
        "validation_result": None,
        "pr_status": "pending",
        "ci_status": "pending",
        "ci_check_executed": False,
        "report_written": False,
        "plan_files_cache": None,
    }


def handle(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Handle PostToolUse(Skill) or UserPromptSubmit to activate workflow."""
    skill, args = _parse_skill_and_args(hook_input)

    if skill not in ("plan", "implement"):
        return "allow", ""

    initial = _initial_state(skill, args)
    store.reinitialize(initial)
    return "allow", ""
