"""validators.py — Backward-compatible wrappers for validator classes.

Each public function delegates to a validator class in the validators/ package.
External consumers import from here; the classes live in validators/*.
"""

from constants import TEST_RUN_PATTERNS
from .state_store import StateStore
from .blockers import (
    Result,
    scores_valid,
    verdict_valid,
    is_agent_report_valid,
    validate_review_sections,
)  # noqa: F401 — re-exported via __all__
from config import Config

from validators.phase_validator import PhaseValidator
from validators.command_validator import CommandValidator
from validators.file_write_validator import FileWriteValidator
from validators.file_edit_validator import FileEditValidator
from validators.agent_validator import AgentValidator
from validators.webfetch_validator import WebFetchValidator


# Re-export for external consumers
__all__ = [
    "is_phase_allowed",
    "is_command_allowed",
    "is_file_write_allowed",
    "is_file_edit_allowed",
    "is_agent_allowed",
    "is_webfetch_allowed",
    "is_test_executed",
    "scores_valid",
    "verdict_valid",
    "is_agent_report_valid",
    "validate_review_sections",
    "_is_test_command",
]


def is_phase_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate phase transition (skill invocation)."""
    return PhaseValidator(hook_input, config, state).validate()


def is_command_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate Bash commands against phase restrictions."""
    return CommandValidator(hook_input, config, state).validate()


def is_file_write_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate file write against phase and path restrictions."""
    return FileWriteValidator(hook_input, config, state).validate()


def is_file_edit_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate file edit against phase and path restrictions."""
    return FileEditValidator(hook_input, config, state).validate()


def is_agent_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate agent invocation against phase and count restrictions."""
    return AgentValidator(hook_input, config, state).validate()


def is_webfetch_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate that a WebFetch URL targets a safe domain."""
    return WebFetchValidator(hook_input, config).validate()


def _is_test_command(command: str) -> bool:
    import re
    return any(re.search(pattern, command) for pattern in TEST_RUN_PATTERNS)


def is_test_executed(command: str) -> Result:
    """Check if the command is a valid test runner."""
    if _is_test_command(command):
        return True, f"Test command recognized: '{command}'"
    raise ValueError(
        f"Command '{command}' is not a valid test command"
        f"\nExpected patterns: {TEST_RUN_PATTERNS}"
    )
