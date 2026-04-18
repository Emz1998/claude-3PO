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
      command must match the phase's whitelist. ``pr-create`` and ``ci-check``
      additionally require ``--json`` on their respective ``gh`` commands so
      downstream parsers can consume structured output.

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

    def _is_read_only_command(self) -> bool:
        """True iff the command starts with any prefix in ``READ_ONLY_COMMANDS``.

        Example:
            >>> guard._is_read_only_command()  # doctest: +SKIP
            True
        """
        return any(self.command.startswith(cmd) for cmd in READ_ONLY_COMMANDS)

    def _is_phase_specific_command(self) -> bool:
        """True iff the command matches the current phase's whitelist.

        Example:
            >>> guard._is_phase_specific_command()  # doctest: +SKIP
            True
        """
        phase_cmds = COMMANDS_MAP.get(self.phase, [])
        return bool(phase_cmds) and any(
            self.command.startswith(cmd) for cmd in phase_cmds
        )

    def _check_read_only(self) -> Decision:
        """
        Allow if read-only, raise otherwise.

        Returns:
            Decision: ``("allow", message)`` for read-only commands.

        Raises:
            ValueError: If the command is not in the read-only whitelist.

        Example:
            >>> decision, message = guard._check_read_only()  # doctest: +SKIP
        """
        if self._is_read_only_command():
            return "allow", f"Read-only command allowed in phase: {self.phase}"
        raise ValueError(
            f"Phase '{self.phase}' only allows read-only commands"
            f"\nAllowed: {READ_ONLY_COMMANDS}"
        )

    def _check_phase_whitelist(self) -> None:
        """
        Enforce the per-phase command-prefix whitelist.

        Raises:
            ValueError: If the phase has a whitelist and the command does
                not start with any of its prefixes.

        Example:
            >>> # Raises ValueError when the command is not in the phase whitelist:
            >>> guard._check_phase_whitelist()  # doctest: +SKIP
        """
        allowed = COMMANDS_MAP.get(self.phase, [])
        if allowed and not any(self.command.startswith(cmd) for cmd in allowed):
            raise ValueError(
                f"Command '{self.command}' not allowed in phase: {self.phase}"
                f"\nAllowed: {allowed}"
            )

    def _check_pr_create_json(self) -> None:
        """
        Require ``--json`` on ``gh pr create`` so the URL/etc can be parsed.

        Raises:
            ValueError: If a ``gh pr create`` command omits the flag.

        Example:
            >>> # Raises ValueError when --json is missing on gh pr create:
            >>> guard._check_pr_create_json()  # doctest: +SKIP
        """
        if self.command.startswith("gh pr create") and "--json" not in self.command:
            raise ValueError(
                f"PR create command must include --json flag\nGot: {self.command}"
            )

    def _check_ci_check_json(self) -> None:
        """
        Require ``--json`` on ``gh pr checks`` so check status can be parsed.

        Raises:
            ValueError: If a ``gh pr checks`` command omits the flag.

        Example:
            >>> # Raises ValueError when --json is missing on gh pr checks:
            >>> guard._check_ci_check_json()  # doctest: +SKIP
        """
        if self.command.startswith("gh pr checks") and "--json" not in self.command:
            raise ValueError(
                f"CI check command must include --json flag\nGot: {self.command}"
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
            # Read-only phases: allow phase-specific commands + read-only commands
            if self.phase in self.config.read_only_phases:
                if self._is_phase_specific_command():
                    return "allow", f"Command allowed in phase: {self.phase}"
                return self._check_read_only()

            # Docs phases: read-only only
            if self.phase in self.config.docs_write_phases:
                return self._check_read_only()

            # Read-only commands allowed in any phase
            if self._is_read_only_command():
                return "allow", f"Read-only command allowed in phase: {self.phase}"

            # Phase-specific whitelist
            self._check_phase_whitelist()

            if self.phase == "pr-create":
                self._check_pr_create_json()
            if self.phase == "ci-check":
                self._check_ci_check_json()

            return "allow", f"Command '{self.command}' allowed in phase: {self.phase}"
        except ValueError as e:
            return "block", str(e)
