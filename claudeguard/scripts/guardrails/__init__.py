"""Guardrails package — tool dispatch map for PreToolUse hook."""

from typing import Literal

from lib.state_store import StateStore
from config import Config

from .phase_guard import PhaseValidator
from .command_validator import CommandValidator
from .write_guard import FileWriteValidator
from .edit_guard import FileEditValidator
from .agent_guard import AgentValidator
from .webfetch_guard import WebFetchValidator
from .agent_report_guard import AgentReportGuard
from .task_create_guard import handle as task_create_handle


Decision = tuple[Literal["allow", "block"], str]


def phase_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return PhaseValidator(hook_input, config, state).validate()


def command_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return CommandValidator(hook_input, config, state).validate()


def write_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return FileWriteValidator(hook_input, config, state).validate()


def edit_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return FileEditValidator(hook_input, config, state).validate()


def agent_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return AgentValidator(hook_input, config, state).validate()


def webfetch_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return WebFetchValidator(hook_input, config).validate()


TOOL_GUARDS: dict[str, callable] = {
    "Skill": phase_guard,
    "Bash": command_guard,
    "Write": write_guard,
    "Edit": edit_guard,
    "Agent": agent_guard,
    "WebFetch": webfetch_guard,
    "TaskCreate": task_create_handle,
}

def agent_report_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return AgentReportGuard(hook_input, config, state).validate()


STOP_GUARDS: dict[str, callable] = {
    "agent_report": agent_report_guard,
}
