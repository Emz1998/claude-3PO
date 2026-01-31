#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json, set_cache, load_cache, save_cache, get_cache

from utils.cache import get_session_id

sys.path.insert(0, str(Path(__file__).parent))
from state import get_state, set_state, load_state  # type: ignore
from _roadmap.project import get_project_milestone_subdir_path, MilestoneSubdir  # type: ignore


DELIVERABLES_FILE_PATHS_CONFIG = {
    "explore": f"{get_project_milestone_subdir_path('codebase-status')}/codebase-status_{get_session_id()}_{datetime.now().strftime('%m%d%Y')}.md",
    "plan": f"{get_project_milestone_subdir_path('plans')}/plan_{get_session_id()}_{datetime.now().strftime('%m%d%Y')}.md",
    "plan-consult": f"{get_project_milestone_subdir_path('consults')}/plan_consultation_{get_session_id()}_{datetime.now().strftime('%m%d%Y')}.md",
    "code": f"{get_project_milestone_subdir_path('code')}/code_{get_session_id()}_{datetime.now().strftime('%m%d%Y')}.md",
    "commit": f"{get_project_milestone_subdir_path('commit')}/commit_{get_session_id()}_{datetime.now().strftime('%m%d%Y')}.md",
}


def are_all_deliverables_met(
    phase_name: str | None = None, state: dict | None = None
) -> bool:
    if state is None:
        state = load_state()
    if not phase_name:
        phase_name = state.get("current_phase", "")
    deliverables_state = state.get("deliverables", {})
    if phase_name not in deliverables_state:
        # No deliverables defined for this phase = consider met
        return True
    phase_deliverables = deliverables_state.get(phase_name, {})
    if not phase_deliverables:
        return True
    return all(
        deliverable_status is True for deliverable_status in phase_deliverables.values()
    )


def main():
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    command = tool_input.get("command", "")
    if hook_event_name != "PostToolUse":
        return

    if tool_name not in ["Write", "Edit", "Bash"]:
        return

    value = file_path or command
    print(f"Value: {value}")
    set_state("deliverables", {value: True})


if __name__ == "__main__":
    print(
        [
            DELIVERABLES_FILE_PATHS_CONFIG[phase]
            for phase in DELIVERABLES_FILE_PATHS_CONFIG
        ]
    )
