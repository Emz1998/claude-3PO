#!/usr/bin/env python3
"""State management for workflow hooks."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple
from dataclasses import dataclass, field

DEFAULT_STATE_FILE_PATH = Path(__file__).parent.parent / "state" / "workflow.json"
DEFAULT_CONFIG_FILE_PATH = Path(__file__).parent.parent / "config" / "workflow.yaml"

DEFAULT_STATE: dict[str, Any] = {
    "workflow_active": False,
    "current_phase": "explore",
    "current_subphase": None,
    "current_coding_phase": None,
    "current_tool": None,
    "development_mode": "tdd",
    "phase_history": [],
    "subphase_index": 0,
    "tools_used": [],
    "subagents_invoked": [],
    "work_done": {
        "files_written": [],
        "files_edited": [],
        "files_read": [],
        "commands_run": [],
        "skills_used": [],
    },
    "deliverables_met": [],
    "acceptance_criteria": {"items": [], "all_met": False},
    "_updated": None,
}


class PhaseTransitionError(Exception):
    """Exception raised for phase transition errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class WorkflowState:
    workflow_active: bool
    current_phase: str = "explore"
    current_subphase: str | None = None
    current_coding_phase: str | None = None
    current_tool: str | None = None
    development_mode: str = "tdd"
    phase_history: list[str] = field(default_factory=list)
    subphase_index: int = 0
    tools_used: list[str] = field(default_factory=list)
    subagents_invoked: list[str] = field(default_factory=list)
    work_done: dict[str, Any] = field(
        default_factory=lambda: {
            "files_written": [],
            "files_edited": [],
            "files_read": [],
            "commands_run": [],
            "skills_used": [],
        }
    )
    deliverables_met: list[str] = field(default_factory=list)
    acceptance_criteria: dict[str, Any] = field(
        default_factory=lambda: {"items": [], "all_met": False}
    )
    _updated: str | None = None


class WorkflowStateManager:
    def __init__(
        self,
        hook_input: dict[str, Any],
        state_file_path: Path = DEFAULT_STATE_FILE_PATH,
        config_file_path: Path = DEFAULT_CONFIG_FILE_PATH,
    ):
        self._state_file_path = state_file_path
        self._config_file_path = config_file_path
        self._hook_input = hook_input
        self._states = self._load_state()
        self._config: dict[str, Any] | None = None

    def _load_state(self) -> WorkflowState:
        """Load state from file or return defaults."""
        if not self._state_file_path.exists():
            return WorkflowState(**DEFAULT_STATE)
        try:
            data = json.loads(self._state_file_path.read_text())
            merged = {**DEFAULT_STATE, **data}
            return WorkflowState(**merged)
        except (json.JSONDecodeError, IOError, TypeError):
            return WorkflowState(**DEFAULT_STATE)

    def _load_config(self) -> dict[str, Any]:
        """Load workflow config from YAML (cached)."""
        if self._config is not None:
            return self._config
        try:
            import yaml
            self._config = yaml.safe_load(self._config_file_path.read_text())
            return self._config or {}
        except (IOError, Exception):
            return {}

    def save_state(self) -> bool:
        """Save state to JSON file."""
        self._state_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._states._updated = datetime.now().isoformat()
        self._state_file_path.write_text(json.dumps(self._states.__dict__, indent=2))
        return True

    @property
    def state_file_path(self) -> Path:
        """Get state file path."""
        return self._state_file_path

    @state_file_path.setter
    def state_file_path(self, value: Path) -> None:
        """Set state file path."""
        self._state_file_path = value

    @property
    def states(self) -> WorkflowState:
        """Get state."""
        return self._states

    @states.setter
    def states(self, value: WorkflowState) -> None:
        """Set state."""
        self._states = value

    @property
    def hook_input(self) -> dict[str, Any]:
        """Get hook input."""
        return self._hook_input

    @hook_input.setter
    def hook_input(self, value: dict[str, Any]) -> None:
        """Set hook input."""
        self._hook_input = value

    def get_state(self, state: str) -> Any | None:
        """Get workflow state."""
        if state not in self._states.__dict__:
            raise ValueError(f"State {state} not found in state.")
        return self._states.__dict__.get(state, None)

    def set_state(self, state: str, value: Any) -> None:
        """Set workflow state."""
        if state not in self._states.__dict__:
            raise ValueError(f"State {state} not found in state.")
        self._states.__dict__[state] = value
        self.save_state()

    def reset_state(self) -> None:
        """Reset state to defaults."""
        self._states = WorkflowState(**DEFAULT_STATE)
        self.save_state()

    def is_workflow_active(self) -> bool | None:
        """Check if workflow is active."""
        return self.get_state("workflow_active")

    def set_workflow_active(self, value: bool) -> None:
        """Set workflow active."""
        self.set_state("workflow_active", value)

    def _set_phase_history(self, phase: str) -> None:
        """Set phase history."""
        phase_history: list[str] = self.get_state("phase_history") or []
        if phase in phase_history:
            return
        phase_history.append(phase)
        self.set_state("phase_history", phase_history)

    def validate_phase_transition(self, new_phase: str) -> Tuple[bool, str]:
        """
        Validate if transitioning to new_phase is allowed.

        Checks:
        1. Phase exists in config
        2. Prerequisites (requires_phase) are met
        3. Sequential order (no skipping, no backwards)

        Returns (allowed, reason).
        """
        config = self._load_config()
        current_phase = self.get_state("current_phase")
        phase_history = self.get_state("phase_history") or []

        # Get phase config
        phases = config.get("phases", [])
        new_phase_config = None
        for p in phases:
            if p.get("name") == new_phase:
                new_phase_config = p
                break

        if not new_phase_config:
            return False, f"Unknown phase: {new_phase}"

        # Check prerequisite phase
        requires = new_phase_config.get("requires_phase")
        if requires and requires not in phase_history:
            return False, f"Phase '{new_phase}' requires completing '{requires}' first"

        # Check sequential order for main phases
        phase_order = config.get("main_phases_order", [])
        if new_phase in phase_order and current_phase in phase_order:
            new_idx = phase_order.index(new_phase)
            current_idx = phase_order.index(current_phase)

            # Can't go backwards
            if new_idx < current_idx:
                return False, f"Cannot go backwards from '{current_phase}' to '{new_phase}'"

            # Can't skip phases
            if new_idx > current_idx + 1:
                skipped = phase_order[current_idx + 1 : new_idx]
                return False, f"Cannot skip phases {skipped}. Complete them first."

        return True, ""

    def advance_phase(self, new_phase: str, force: bool = False) -> None:
        """
        Advance to a new phase with validation.

        Args:
            new_phase: The phase to transition to
            force: If True, skip validation (use with caution)

        Raises:
            PhaseTransitionError: If transition is not allowed
        """
        if not force:
            allowed, reason = self.validate_phase_transition(new_phase)
            if not allowed:
                raise PhaseTransitionError(reason)

        self.set_state("current_phase", new_phase)
        self._set_phase_history(new_phase)
        # Clear subphase when entering new main phase
        self.set_state("current_subphase", None)
        # Clear deliverables for new phase
        self.set_state("deliverables_met", [])

    def advance_subphase(self, new_subphase: str) -> None:
        """
        Advance to a new subphase within the code phase.

        Args:
            new_subphase: The subphase to transition to

        Raises:
            PhaseTransitionError: If not in code phase or invalid subphase
        """
        current_phase = self.get_state("current_phase")
        if current_phase != "code":
            raise PhaseTransitionError(
                f"Can only set subphase in 'code' phase, currently in '{current_phase}'"
            )

        config = self._load_config()
        mode = self.get_state("development_mode") or "tdd"
        coding_order = config.get("coding_phases_order", {}).get(mode, [])

        if new_subphase not in coding_order:
            raise PhaseTransitionError(
                f"Unknown subphase '{new_subphase}' for mode '{mode}'"
            )

        current_subphase = self.get_state("current_subphase")
        if current_subphase and current_subphase in coding_order:
            current_idx = coding_order.index(current_subphase)
            new_idx = coding_order.index(new_subphase)

            if new_idx < current_idx:
                raise PhaseTransitionError(
                    f"Cannot go backwards from '{current_subphase}' to '{new_subphase}'"
                )
            if new_idx > current_idx + 1:
                skipped = coding_order[current_idx + 1 : new_idx]
                raise PhaseTransitionError(
                    f"Cannot skip subphases {skipped}. Complete them first."
                )

        self.set_state("current_subphase", new_subphase)
        self.set_state("subphase_index", coding_order.index(new_subphase))
        # Clear deliverables for new subphase
        self.set_state("deliverables_met", [])

    def advance_coding_phase(self) -> None:
        """Advance to a new coding phase."""
        phase = self.get_state("current_phase")
        if phase != "code":
            return
        self.set_state("current_coding_phase", None)
        self.set_state("subphase_index", 0)

    def set_current_tool(self, tool_name: str) -> None:
        """Set current tool."""
        self.set_state("current_tool", tool_name)

    def get_current_tool(self) -> str | None:
        """Get current tool."""
        return self.get_state("current_tool")

    def record_tool_used(self, tool_name: str) -> None:
        """Record a tool use in state."""
        tools_used: list[str] = self.get_state("tools_used") or []
        tools_used.append(tool_name)
        self.set_state("tools_used", tools_used)

    def record_file_written(self, file_path: str) -> None:
        """Record a file written in state."""
        work_done: dict[str, Any] = self.get_state("work_done") or {}
        files_written: list[str] = work_done.get("files_written", []) or []
        if file_path in files_written:
            return
        files_written.append(file_path)
        work_done["files_written"] = files_written
        self.set_state("work_done", work_done)

    def record_subagent_invoked(self, subagent_name: str) -> None:
        """Record a subagent invoked in state."""
        subagents_invoked: list[str] = self.get_state("subagents_invoked") or []
        if subagent_name in subagents_invoked:
            return
        subagents_invoked.append(subagent_name)
        self.set_state("subagents_invoked", subagents_invoked)

    def set_deliverables_met(self, deliverables: list[str]) -> None:
        """Set deliverables met in state."""
        self.set_state("deliverables_met", deliverables)

    def add_deliverable_met(self, deliverable: str) -> None:
        """Add a deliverable to the met list."""
        deliverables: list[str] = self.get_state("deliverables_met") or []
        if deliverable not in deliverables:
            deliverables.append(deliverable)
            self.set_state("deliverables_met", deliverables)

    def set_all_acs_met(self, met: bool) -> None:
        """Record if all acceptance criteria are met in state."""
        ac: dict[str, Any] = self.get_state("acceptance_criteria") or {}
        ac["all_met"] = met
        self.set_state("acceptance_criteria", ac)

    def set_development_mode(self, mode: str) -> None:
        """Set development mode."""
        self.set_state("development_mode", mode)

    def set_current_coding_phase(self, phase: str) -> None:
        """Set current coding phase."""
        self.set_state("current_coding_phase", phase)

    def set_current_subphase(self, subphase: str | None) -> None:
        """Set current subphase."""
        self.set_state("current_subphase", subphase)

    def get_state_dict(self) -> dict[str, Any]:
        """Get state as dictionary."""
        return self._states.__dict__.copy()


# Module-level helper functions for backward compatibility
def is_workflow_active(state_file_path: Path = DEFAULT_STATE_FILE_PATH) -> bool:
    """Check if workflow is active (module-level helper)."""
    if not state_file_path.exists():
        return False
    try:
        data = json.loads(state_file_path.read_text())
        return data.get("workflow_active", False)
    except (json.JSONDecodeError, IOError):
        return False


def get_state(state_file_path: Path = DEFAULT_STATE_FILE_PATH) -> dict[str, Any]:
    """Get state as dictionary (module-level helper)."""
    if not state_file_path.exists():
        return DEFAULT_STATE.copy()
    try:
        data = json.loads(state_file_path.read_text())
        return {**DEFAULT_STATE, **data}
    except (json.JSONDecodeError, IOError):
        return DEFAULT_STATE.copy()


def advance_phase(
    new_phase: str,
    force: bool = False,
    state_file_path: Path = DEFAULT_STATE_FILE_PATH,
    config_file_path: Path = DEFAULT_CONFIG_FILE_PATH,
) -> Tuple[bool, str]:
    """
    Advance to a new phase with validation (module-level helper).

    Returns (success, error_message).
    """
    manager = WorkflowStateManager(
        hook_input={},
        state_file_path=state_file_path,
        config_file_path=config_file_path,
    )
    try:
        manager.advance_phase(new_phase, force=force)
        return True, ""
    except PhaseTransitionError as e:
        return False, e.message


def advance_subphase(
    new_subphase: str,
    state_file_path: Path = DEFAULT_STATE_FILE_PATH,
    config_file_path: Path = DEFAULT_CONFIG_FILE_PATH,
) -> Tuple[bool, str]:
    """
    Advance to a new subphase with validation (module-level helper).

    Returns (success, error_message).
    """
    manager = WorkflowStateManager(
        hook_input={},
        state_file_path=state_file_path,
        config_file_path=config_file_path,
    )
    try:
        manager.advance_subphase(new_subphase)
        return True, ""
    except PhaseTransitionError as e:
        return False, e.message


if __name__ == "__main__":
    error = PhaseTransitionError("Phase already in phase history.")
    print(error.message)
