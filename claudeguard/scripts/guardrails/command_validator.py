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
    """Validate Bash commands against phase restrictions."""

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.command = hook_input.get("tool_input", {}).get("command", "")

    # ── Checks ────────────────────────────────────────────────────

    def _is_read_only_command(self) -> bool:
        return any(self.command.startswith(cmd) for cmd in READ_ONLY_COMMANDS)

    def _is_phase_specific_command(self) -> bool:
        phase_cmds = COMMANDS_MAP.get(self.phase, [])
        return bool(phase_cmds) and any(
            self.command.startswith(cmd) for cmd in phase_cmds
        )

    def _check_read_only(self) -> Decision:
        if self._is_read_only_command():
            return "allow", f"Read-only command allowed in phase: {self.phase}"
        raise ValueError(
            f"Phase '{self.phase}' only allows read-only commands"
            f"\nAllowed: {READ_ONLY_COMMANDS}"
        )

    def _check_phase_whitelist(self) -> None:
        allowed = COMMANDS_MAP.get(self.phase, [])
        if allowed and not any(self.command.startswith(cmd) for cmd in allowed):
            raise ValueError(
                f"Command '{self.command}' not allowed in phase: {self.phase}"
                f"\nAllowed: {allowed}"
            )

    def _check_pr_create_json(self) -> None:
        if self.command.startswith("gh pr create") and "--json" not in self.command:
            raise ValueError(
                f"PR create command must include --json flag\nGot: {self.command}"
            )

    def _check_ci_check_json(self) -> None:
        if self.command.startswith("gh pr checks") and "--json" not in self.command:
            raise ValueError(
                f"CI check command must include --json flag\nGot: {self.command}"
            )

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """Returns ("allow", message) or ("block", reason)."""
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
