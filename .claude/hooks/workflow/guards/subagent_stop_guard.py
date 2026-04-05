"""subagent_stop_guard.py — Validate agent output schema on SubagentStop.

Blocks if the agent's last_assistant_message doesn't match the expected
report format for agents that have a defined output schema.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_store import SessionStore

QA_REQUIRED_SECTIONS = [
    "## QA Report",
    "### Criteria Checklist",
    "### Test Results",
    "### Final Verdict",
]

AGENT_SCHEMAS: dict[str, list[str]] = {
    "QualityAssurance": QA_REQUIRED_SECTIONS,
}


def validate(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Validate SubagentStop output against expected schema.

    Returns ("allow", "") or ("block", reason).
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    agent_type = hook_input.get("agent_type", "")
    required_sections = AGENT_SCHEMAS.get(agent_type)
    if not required_sections:
        return "allow", ""

    message = hook_input.get("last_assistant_message", "")
    missing = [s for s in required_sections if s not in message]
    if missing:
        return (
            "block",
            f"Blocked: {agent_type} response missing required sections: {', '.join(missing)}. "
            f"Re-run the {agent_type} agent with the correct output format.",
        )

    return "allow", ""
