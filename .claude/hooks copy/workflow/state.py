#!/usr/bin/env python3
"""PostToolUse hook for workflow state tracking."""

import json
import sys
import re
import yaml
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

CONFIG_PATH = Path(__file__).parent / "config.yaml"
STATE_PATH = Path(__file__).parent / "state.json"


def load_config(path: Path) -> dict:
    if path.exists():
        return yaml.safe_load(path.read_text())
    return {}


def load_state(state_path: Path = STATE_PATH) -> dict:
    if state_path.exists():
        try:
            return json.loads(state_path.read_text())
        except (json.JSONDecodeError, IOError, TypeError):
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def set_state(key: str, value: Any, state: dict | None = None) -> None:
    if not state:
        state = load_state()
    state[key] = value
    save_state(state)


def get_state(key: str, state: dict | None = None) -> Any | None:
    if not state:
        state = load_state()
    return state.get(key, None)


def _add_deliverables(
    init_deliverable: dict[str, dict[str, bool]],
    phase: str,
    phase_config: dict,
) -> None:
    """Extract file_paths and commands from config and add to init_deliverable."""
    deliverables = phase_config.get("file_paths", []) + phase_config.get("commands", [])
    if deliverables:
        init_deliverable.setdefault(phase, {})
        for item in deliverables:
            init_deliverable[phase][item] = False


def initialize_deliverables_state(
    config: dict | None = None,
    test_strategy: str = "tdd",
    state: dict | None = None,
) -> dict:
    if not config:
        config = load_config(CONFIG_PATH)
    if not state:
        state = load_state()

    deliverables_state = state.get("deliverables", {})
    init_deliverable: dict[str, dict[str, bool]] = {}

    for phase, value in config.items():
        if phase == "code" and test_strategy in value:
            for subphase_config in value.get(test_strategy, {}).values():
                _add_deliverables(init_deliverable, phase, subphase_config)
        else:
            _add_deliverables(init_deliverable, phase, value)

    state["deliverables"] = {**deliverables_state, **init_deliverable}
    return state


def reset_deliverables_state() -> None:
    initialize_deliverables_state()


def get_deliverable_state(deliverable_name: str = "", state: dict = {}) -> dict:
    deliverables = state.get("deliverables", [])
    if not deliverable_name:
        return {}
    for d in deliverables:
        if d["name"] == deliverable_name:
            return d
    return {}


def check_matches(value: str, patterns: list[str]) -> bool:
    for p in patterns:
        if bool(re.match(p, value)):
            return True
    return False


def log_deliverable_status(tool_value: str, state: dict | None = None) -> None:
    if not state:
        state = load_state()

    current_phase = state.get("current_phase", "")
    if not current_phase:
        return

    deliverables_state = state.get("deliverables", {})
    phase_deliverables = deliverables_state.get(current_phase, {})
    if not phase_deliverables:
        return

    matched = False
    for pattern in phase_deliverables:
        if re.match(pattern, tool_value):
            phase_deliverables[pattern] = True
            matched = True
            break

    if matched:
        deliverables_state[current_phase] = phase_deliverables
        state["deliverables"] = deliverables_state
        save_state(state)


def are_all_deliverables_met(
    phase_name: str | None = None, state: dict | None = None
) -> bool:
    if not state:
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


def initialize_state(state: dict | None = None) -> None:
    if not state:
        state = load_state()

    default_deliverables = initialize_deliverables_state()

    default_state = {
        "workflow_active": False,
        "current_phase": "explore",
        "read_files": {},
        "written_files": [],
        "edited_files": [],
        "troubleshoot": False,
        "phase_history": [],
        "deliverables": default_deliverables.get("deliverables", {}),
    }
    state = default_state.copy()
    save_state(state)


def reset_state() -> None:
    initialize_state()
