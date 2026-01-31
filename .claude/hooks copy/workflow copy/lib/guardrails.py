# .claude/hooks/workflow/lib/guardrails.py
"""
Guardrails for workflow enforcement.
Validates subagents, phases, subphases, and stop conditions based on workflow.yaml schema.
"""
import re
import json
import yaml
from pathlib import Path
from typing import Tuple, Optional, List, Literal

CONFIG_NAMES = Literal["workflow", "phases"]


def load_config(file_name: CONFIG_NAMES = "workflow") -> dict | List[dict]:
    """Load workflow configuration from YAML."""
    path = Path(__file__).parent.parent / Path(f"config/{file_name}.yaml")
    config = yaml.safe_load(path.read_text())
    if isinstance(config, list):
        return config
    return config


def get_phase(config: dict, phase_name: str) -> Optional[dict]:
    """Get phase configuration by name from phases list."""
    phases = config.get("phases", [])
    for phase in phases:
        if phase.get("name") == phase_name:
            return phase
    return None


def get_subphase(config: dict, subphase_name: str) -> Optional[dict]:
    """Get subphase configuration by name. Subphases are defined as phases themselves."""
    return get_phase(config, subphase_name)


def get_coding_workflow_order(config: dict, state: dict) -> List[str]:
    """Get the subphase order based on development mode (tdd or test_after)."""
    coding_phases = config.get("coding_phases_order", {})
    mode = state.get("development_mode", "tdd")
    return coding_phases.get(mode, [])


def check_subagent_allowed(
    config: dict, state: dict, subagent: str
) -> Tuple[bool, str]:
    """Check if subagent matches the agent_owner for current phase/subphase."""
    subphase = state.get("current_subphase")
    phase = state.get("current_phase")

    # Check subphase first (takes precedence)
    if subphase:
        cfg = get_phase(config, subphase)
        if cfg:
            owner = cfg.get("agent_owner")
            if owner and subagent != owner:
                return False, f"Subphase '{subphase}' owned by '{owner}', not '{subagent}'"
            return True, ""

    # Check phase
    if not phase:
        return False, "No current phase set"

    cfg = get_phase(config, phase)
    if not cfg:
        return False, f"Unknown phase: {phase}"

    owner = cfg.get("agent_owner")

    # Phase has subphases but no owner = requires subphase
    if not owner and cfg.get("subphases"):
        return False, f"Phase '{phase}' requires a subphase. Set current_subphase first."

    if owner and subagent != owner:
        return False, f"Phase '{phase}' owned by '{owner}', not '{subagent}'"

    return True, ""


def check_phase_transition(
    config: dict, state: dict, new_phase: str
) -> Tuple[bool, str]:
    """Check if transitioning to new phase is allowed. Returns (allowed, reason)."""
    new_phase_config = get_phase(config, new_phase)
    if not new_phase_config:
        return False, f"Unknown phase: {new_phase}"

    # Check prerequisite phase
    requires = new_phase_config.get("requires_phase")
    if requires and requires not in state.get("phase_history", []):
        return False, f"Phase '{new_phase}' requires completing '{requires}' first"

    return True, ""


def validate_write_file_path(config: dict, current_phase: str, file_path: str) -> bool:
    """Validate tool input based on workflow configuration."""
    if not file_path:
        return True
    phase = get_phase(config, current_phase)
    if not phase:
        return True
    for deliverable in phase.get("required_deliverables", []):
        tools = deliverable.get("tool")
        if isinstance(tools, list):
            if "Write" not in tools:
                continue
        elif tools != "Write":
            continue
        if "pattern" in deliverable and _matches_pattern(file_path, deliverable["pattern"]):
            return True
        if "file_path" in deliverable and _matches_pattern(file_path, deliverable["file_path"]):
            return True
        if "extensions" in deliverable and Path(file_path).suffix in deliverable["extensions"]:
            return True
    return False


def validate_edit_file_path(config: dict, current_phase: str, file_path: str) -> bool:
    """Validate tool input based on workflow configuration."""
    if not file_path:
        return True
    phase = get_phase(config, current_phase)
    if not phase:
        return True
    for deliverable in phase.get("required_deliverables", []):
        tools = deliverable.get("tool")
        if isinstance(tools, list):
            if "Edit" not in tools:
                continue
        elif tools != "Edit":
            continue
        if "pattern" in deliverable and _matches_pattern(file_path, deliverable["pattern"]):
            return True
        if "file_path" in deliverable and _matches_pattern(file_path, deliverable["file_path"]):
            return True
        if "extensions" in deliverable and Path(file_path).suffix in deliverable["extensions"]:
            return True
    return False


def validate_bash_command(config: dict, current_phase: str, command: str) -> bool:
    """Validate tool input based on workflow configuration."""
    if not command:
        return True
    phase = get_phase(config, current_phase)
    if not phase:
        return True
    for deliverable in phase.get("required_deliverables", []):
        if deliverable.get("tool") != "Bash":
            continue
        pattern = deliverable.get("pattern")
        if pattern and pattern in command:
            return True
    return False


def validate_phase_transition(
    phase_order: list[str], current_phase: str, new_phase: str
) -> Tuple[bool, str]:
    """Validate phase transition based on workflow configuration."""
    if new_phase not in phase_order:
        return False, f"Phase '{new_phase}' not in phase order"
    if current_phase not in phase_order:
        return False, f"Current phase '{current_phase}' not in phase order"
    expected_idx = phase_order.index(new_phase)
    current_idx = phase_order.index(current_phase)
    if expected_idx < current_idx:
        return False, f"Phase '{new_phase}' already completed. Cannot go backwards."
    if expected_idx > current_idx + 1:
        skipped = phase_order[current_idx + 1 : expected_idx]
        return False, f"Must complete {skipped} before '{new_phase}'"
    return True, ""


def check_can_stop(
    config: dict,
    state: dict,
    agent_type: Literal["main_agent", "subagent"] = "main_agent"
) -> Tuple[bool, str]:
    """Check if agent can stop based on stop_conditions in config."""
    stop_conditions = config.get("stop_conditions", {})
    condition_key = "main_agent" if agent_type == "main_agent" else "subagents"
    conditions = stop_conditions.get(condition_key, [])

    # Check each required condition
    for condition in conditions:
        if condition == "all_acs_met":
            ac = state.get("acceptance_criteria", {})
            if not ac.get("all_met", False):
                return False, "Cannot stop: not all acceptance criteria met"

        if condition == "all_deliverables_met":
            deliverables = state.get("deliverables_met", [])
            if not deliverables:
                return False, "Cannot stop: no deliverables met"

    return True, ""


def _get_deliverables(config: dict, state: dict) -> list:
    """Get deliverables from current subphase or phase."""
    subphase = state.get("current_subphase")
    if subphase:
        cfg = get_phase(config, subphase)
        return cfg.get("required_deliverables", []) if cfg else []

    phase = state.get("current_phase")
    if phase:
        cfg = get_phase(config, phase)
        return cfg.get("required_deliverables", []) if cfg else []
    return []


def _tool_matches(tool_name: str, req_tool: str | list | None) -> bool:
    """Check if tool_name matches required tool specification."""
    if not req_tool:
        return True
    if isinstance(req_tool, list):
        return tool_name in req_tool
    return tool_name == req_tool


def check_deliverable_met(
    config: dict, state: dict, tool_name: str, tool_input: dict
) -> Tuple[bool, Optional[str]]:
    """Check if a deliverable was met. Returns (met, name)."""
    deliverables = _get_deliverables(config, state)
    if not deliverables:
        return False, None

    file_path = tool_input.get("file_path", "")
    command = tool_input.get("command", "")

    for d in deliverables:
        # String pattern - simple file match
        if isinstance(d, str):
            if tool_name in ["Write", "Edit"] and _matches_pattern(file_path, d):
                return True, d
            continue

        # Skip if tool doesn't match
        if not _tool_matches(tool_name, d.get("tool")):
            continue

        # File deliverable with pattern
        if tool_name in ["Write", "Edit"]:
            if "pattern" in d and _matches_pattern(file_path, d["pattern"]):
                return True, d["pattern"]
            if "extensions" in d and Path(file_path).suffix in d["extensions"]:
                return True, Path(file_path).suffix

        # Bash command deliverable
        if tool_name == "Bash":
            pattern = d.get("pattern")
            if pattern and pattern in command:
                return True, pattern

        # Skill deliverable
        if tool_name == "Skill":
            skill = tool_input.get("skill", "")
            pattern = d.get("pattern")
            if pattern and _matches_pattern(skill, pattern):
                return True, skill

    return False, None


def _matches_pattern(value: str, pattern: str) -> bool:
    """Pattern matching for file paths or skill names using regex."""
    if not value or not pattern:
        return False
    try:
        return bool(re.search(pattern, value))
    except re.error:
        # Fallback to simple contains check if regex is invalid
        return pattern in value


if __name__ == "__main__":
    # Quick test
    workflow_config = load_config("workflow")
    print(json.dumps(workflow_config, indent=2))
