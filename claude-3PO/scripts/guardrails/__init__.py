"""Guardrails package — tool dispatch map for PreToolUse / Stop hooks."""

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
    """
    Validate a Skill (phase transition) invocation.

    Args:
        hook_input (dict): Raw PreToolUse hook payload from Claude Code.
        config (Config): Workflow configuration.
        state (StateStore): Mutable workflow state snapshot.

    Returns:
        Decision: ``("allow", message)`` if the transition is legal, otherwise
        ``("block", reason)``.

    Example:
        >>> decision, message = phase_guard(hook_input, config, state)  # doctest: +SKIP
        >>> decision  # doctest: +SKIP
        'allow'
    """
    return PhaseGuard(hook_input, config, state).validate()


def command_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    """
    Validate a Bash command against the current phase whitelist.

    Args:
        hook_input (dict): Raw PreToolUse hook payload.
        config (Config): Workflow configuration.
        state (StateStore): Mutable workflow state snapshot.

    Returns:
        Decision: Allow/block decision tuple.

    Example:
        >>> decision, message = command_guard(hook_input, config, state)  # doctest: +SKIP
        >>> decision  # doctest: +SKIP
        'allow'
    """
    return CommandGuard(hook_input, config, state).validate()


def write_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    """
    Validate a Write tool invocation against phase + path rules.

    Args:
        hook_input (dict): Raw PreToolUse hook payload.
        config (Config): Workflow configuration.
        state (StateStore): Mutable workflow state snapshot.

    Returns:
        Decision: Allow/block decision tuple.

    Example:
        >>> decision, message = write_guard(hook_input, config, state)  # doctest: +SKIP
        >>> decision  # doctest: +SKIP
        'allow'
    """
    return FileWriteGuard(hook_input, config, state).validate()


def edit_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    """
    Validate an Edit tool invocation against phase + path rules.

    Args:
        hook_input (dict): Raw PreToolUse hook payload.
        config (Config): Workflow configuration.
        state (StateStore): Mutable workflow state snapshot.

    Returns:
        Decision: Allow/block decision tuple.

    Example:
        >>> decision, message = edit_guard(hook_input, config, state)  # doctest: +SKIP
        >>> decision  # doctest: +SKIP
        'allow'
    """
    return FileEditGuard(hook_input, config, state).validate()


def agent_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    """
    Validate an Agent invocation against phase + per-agent count limits.

    Args:
        hook_input (dict): Raw PreToolUse hook payload.
        config (Config): Workflow configuration.
        state (StateStore): Mutable workflow state snapshot.

    Returns:
        Decision: Allow/block decision tuple.

    Example:
        >>> decision, message = agent_guard(hook_input, config, state)  # doctest: +SKIP
        >>> decision  # doctest: +SKIP
        'allow'
    """
    return AgentGuard(hook_input, config, state).validate()


def webfetch_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    """
    Validate a WebFetch URL against the configured safe-domain list.

    Args:
        hook_input (dict): Raw PreToolUse hook payload.
        config (Config): Workflow configuration (provides ``safe_domains``).
        state (StateStore): Unused — accepted for dispatch-signature uniformity.

    Returns:
        Decision: Allow/block decision tuple.

    Example:
        >>> decision, message = webfetch_guard(hook_input, config, state)  # doctest: +SKIP
        >>> decision  # doctest: +SKIP
        'allow'
    """
    return WebFetchGuard(hook_input, config).validate()


def task_create_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    """
    Validate a TaskCreate tool invocation (parent metadata in implement workflow).

    Args:
        hook_input (dict): Raw PreToolUse hook payload.
        config (Config): Workflow configuration.
        state (StateStore): Mutable workflow state snapshot.

    Returns:
        Decision: Allow/block decision tuple.

    Example:
        >>> decision, message = task_create_guard(hook_input, config, state)  # doctest: +SKIP
        >>> decision  # doctest: +SKIP
        'allow'
    """
    return TaskCreateToolGuard(hook_input, config, state).validate()


# Map tool names to the PreToolUse guard responsible for validating them.
TOOL_GUARDS: dict[str, callable] = {
    "Skill": phase_guard,
    "Bash": command_guard,
    "Write": write_guard,
    "Edit": edit_guard,
    "Agent": agent_guard,
    "WebFetch": webfetch_guard,
    "TaskCreate": task_create_guard,
    "AskUserQuestion": phase_guard,
}

def agent_report_guard(hook_input: dict, config: Config, state: StateStore) -> Decision:
    """
    Validate an agent's final report at SubagentStop (pure validator).

    Args:
        hook_input (dict): Raw Stop hook payload (must include ``last_assistant_message``).
        config (Config): Workflow configuration.
        state (StateStore): Mutable workflow state snapshot — read only by this guard.

    Returns:
        Decision: Allow/block decision tuple. State mutations (recorder/resolver) are
        applied by the dispatcher after Allow, never by the guard itself.

    Example:
        >>> decision, message = agent_report_guard(hook_input, config, state)  # doctest: +SKIP
        >>> decision  # doctest: +SKIP
        'allow'
    """
    return AgentReportGuard(hook_input, config, state).validate()


# Map Stop-hook event names to the guard responsible for validating them.
STOP_GUARDS: dict[str, callable] = {
    "agent_report": agent_report_guard,
}
