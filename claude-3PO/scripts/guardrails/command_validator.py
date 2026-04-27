"""CommandGuard — Validates Bash commands against phase restrictions."""

from constants import (
    COMMANDS_MAP,
    READ_ONLY_COMMANDS,
)
from typing import Literal

from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class CommandGuard:
    """Validate Bash commands against the current phase's whitelist.

    Three classes of phase get different treatment:

    - ``read_only_phases`` — accept the phase's own command-prefix whitelist
      (from :data:`constants.COMMANDS_MAP`) plus the global read-only set.
    - ``docs_write_phases`` — accept only read-only commands.
    - All other phases — read-only commands are always allowed; otherwise the
      command must match the phase's whitelist.

    Example:
        >>> guard = CommandGuard(hook_input, config, state)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        """
        Cache the bash command string and dependencies.

        Args:
            hook_input (dict): Raw PreToolUse hook payload.
            config (Config): Workflow configuration (read-only / docs phase lists).
            state (StateStore): Mutable workflow state snapshot.

        Example:
            >>> guard = CommandGuard(hook_input, config, state)  # doctest: +SKIP
            >>> guard.command  # doctest: +SKIP
            'ls -la'
        """
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.command = hook_input.get("tool_input", {}).get("command", "")

    # ── Checks ────────────────────────────────────────────────────

    def is_read_only_command(self) -> bool:
        """True iff the command starts with any prefix in ``READ_ONLY_COMMANDS``.

        Example:
            >>> guard.is_read_only_command()  # doctest: +SKIP
            True
        """
        return any(self.command.startswith(cmd) for cmd in READ_ONLY_COMMANDS)

    def is_phase_specific_command(self) -> bool:
        """True iff the command matches the current phase's whitelist.

        Example:
            >>> guard.is_phase_specific_command()  # doctest: +SKIP
            True
        """
        phase_cmds = COMMANDS_MAP.get(self.phase, [])
        return bool(phase_cmds) and any(
            self.command.startswith(cmd) for cmd in phase_cmds
        )

    def check_read_only(self) -> Decision:
        """
        Allow if read-only, raise otherwise.

        Returns:
            Decision: ``("allow", message)`` for read-only commands.

        Raises:
            ValueError: If the command is not in the read-only whitelist.

        Example:
            >>> decision, message = guard.check_read_only()  # doctest: +SKIP
        """
        if self.is_read_only_command():
            return "allow", f"Read-only command allowed in phase: {self.phase}"
        raise ValueError(
            f"Phase '{self.phase}' only allows read-only commands"
            f"\nAllowed: {READ_ONLY_COMMANDS}"
        )

    def check_phase_whitelist(self) -> None:
        """
        Enforce the per-phase command-prefix whitelist.

        Raises:
            ValueError: If the phase has a whitelist and the command does
                not start with any of its prefixes.

        Example:
            >>> # Raises ValueError when the command is not in the phase whitelist:
            >>> guard.check_phase_whitelist()  # doctest: +SKIP
        """
        allowed = COMMANDS_MAP.get(self.phase, [])
        if allowed and not any(self.command.startswith(cmd) for cmd in allowed):
            raise ValueError(
                f"Command '{self.command}' not allowed in phase: {self.phase}"
                f"\nAllowed: {allowed}"
            )

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """
        Return an allow/block decision for the cached Bash command.

        Returns:
            Decision: ``("allow", message)`` if the command is permitted in
            the current phase, otherwise ``("block", reason)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        try:
            # Read-only phases: accept either the phase's own whitelist or the
            # global read-only set — both are considered safe.
            if self.phase in self.config.read_only_phases:
                if self.is_phase_specific_command():
                    return "allow", f"Command allowed in phase: {self.phase}"
                return self.check_read_only()

            # Docs phases may never run non-read-only commands.
            if self.phase in self.config.docs_write_phases:
                return self.check_read_only()

            # Everywhere else: read-only commands are an escape hatch that works
            # regardless of the phase-specific whitelist.
            if self.is_read_only_command():
                return "allow", f"Read-only command allowed in phase: {self.phase}"

            self.check_phase_whitelist()

            return "allow", f"Command '{self.command}' allowed in phase: {self.phase}"
        except ValueError as e:
            return "block", str(e)
