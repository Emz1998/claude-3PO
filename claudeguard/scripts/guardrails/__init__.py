"""Guardrails package — tool dispatch map for PreToolUse hook."""

from typing import Literal

from lib.state_store import StateStore
from config import Config

from .phase_guard import PhaseGuard
from .command_validator import CommandGuard
from .write_guard import FileWriteGuard
from .edit_guard import FileEditGuard
from .agent_guard import AgentGuard
from .webfetch_guard import WebFetchGuard
from .agent_report_guard import AgentReportGuard
from .task_create_tool_guard import TaskCreateToolGuard


Decision = tuple[Literal["allow", "block"], str]


def phase_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return PhaseGuard(hook_input, config, state).validate()


def command_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return CommandGuard(hook_input, config, state).validate()


def write_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return FileWriteGuard(hook_input, config, state).validate()


def edit_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return FileEditGuard(hook_input, config, state).validate()


def agent_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return AgentGuard(hook_input, config, state).validate()


def webfetch_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return WebFetchGuard(hook_input, config).validate()


def task_create_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return TaskCreateToolGuard(hook_input, config, state).validate()


TOOL_GUARDS: dict[str, callable] = {
    "Skill": phase_guard,
    "Bash": command_guard,
    "Write": write_guard,
    "Edit": edit_guard,
    "Agent": agent_guard,
    "WebFetch": webfetch_guard,
    "TaskCreate": task_create_guard,
}

def agent_report_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    return AgentReportGuard(hook_input, config, state).validate()


STOP_GUARDS: dict[str, callable] = {
    "agent_report": agent_report_guard,
}
