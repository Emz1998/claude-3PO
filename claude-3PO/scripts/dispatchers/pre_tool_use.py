#!/usr/bin/env python3
"""PreToolUse hook — dispatches to the appropriate guardrail based on tool_name."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from guardrails import TOOL_GUARDS
from lib.hook import Hook
from lib.state_store import StateStore
from lib.violations import log_violation, extract_action
from config import Config


def resolve_violation_phase(
    state: StateStore, config: Config, tool_name: str, hook_input: dict
) -> str:
    """Pick the best phase label for a violation: skill name, current phase, or first workflow phase."""
    if tool_name == "Skill":
        from lib.extractors import extract_skill_name
        skill = extract_skill_name(hook_input)
        if skill:
            return skill
    if state.current_phase:
        return state.current_phase
    workflow = state.get("workflow_type", "build")
    phases = config.get_phases(workflow) or config.main_phases
    return phases[0] if phases else ""


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(SCRIPTS_DIR / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    guard = TOOL_GUARDS.get(tool_name)
    if not guard:
        sys.exit(0)

    config = Config()

    decision, message = guard(hook_input, config, state)

    if decision == "block":
        log_violation(
            session_id=session_id,
            workflow_type=state.get("workflow_type", "build"),
            story_id=state.get("story_id"),
            prompt_summary=state.get("prompt_summary"),
            phase=resolve_violation_phase(state, config, tool_name, hook_input),
            tool=tool_name,
            action=extract_action(tool_name, hook_input),
            reason=message,
        )
        Hook.advanced_block("PreToolUse", message)
    else:
        Hook.system_message(message)


if __name__ == "__main__":
    main()
