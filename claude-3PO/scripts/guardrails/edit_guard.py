"""FileEditGuard — Validates file edits against phase and path restrictions."""

from typing import Literal

from lib.state_store import StateStore
from lib.paths import is_e2e_report_path, path_matches
from config import Config
from lib.validators import template_conformance_check  # type: ignore
from templates import DEFAULT_PLAN_TEMPLATE  # type: ignore


Decision = tuple[Literal["allow", "block"], str]


class FileEditGuard:
    """Validate an Edit tool call against the current phase + path rules.

    In the trimmed 7-phase MVP only ``plan`` permits Edit — author tweaks to
    the plan file must preserve the required H2 sections (the guard simulates
    the patch and checks the post-edit content).

    Test-mode shortcut: edits to the E2E test report or the state file are
    always allowed when the harness sets ``state.test_mode``.

    Example:
        >>> guard = FileEditGuard(hook_input, config, state)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        """
        Cache the target file path and dependencies.

        Args:
            hook_input (dict): Raw PreToolUse hook payload.
            config (Config): Workflow configuration.
            state (StateStore): Mutable workflow state snapshot.

        Example:
            >>> guard = FileEditGuard(hook_input, config, state)  # doctest: +SKIP
            >>> guard.file_path  # doctest: +SKIP
            'plan.md'
        """
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.file_path = hook_input.get("tool_input", {}).get("file_path", "")

    # ── Checks ────────────────────────────────────────────────────

    def is_test_report(self) -> bool:
        """True iff in test mode and the path is the E2E test report.

        Example:
            >>> guard.is_test_report()  # doctest: +SKIP
            True
        """
        return bool(self.state.get("test_mode")) and is_e2e_report_path(self.file_path)

    def is_state_file(self) -> bool:
        """True iff in test mode and the path ends with ``state.json``.

        Example:
            >>> guard.is_state_file()  # doctest: +SKIP
            True
        """
        return self.state.get("test_mode") and self.file_path.endswith("state.json")

    @property
    def phase_label(self) -> str:
        """Human-readable phase name, or a placeholder when no phase is active.

        Example:
            >>> guard.phase_label  # doctest: +SKIP
            'plan'
        """
        return self.phase or "(no phase active — workflow not started)"

    def check_editable_phase(self) -> None:
        """
        Reject when the current phase isn't one of the edit-capable phases.

        Raises:
            ValueError: If the phase isn't in ``code_edit_phases`` or
                ``docs_edit_phases``.

        Example:
            >>> # Raises ValueError when the current phase doesn't permit edits:
            >>> guard.check_editable_phase()  # doctest: +SKIP
        """
        editable = self.config.code_edit_phases + self.config.docs_edit_phases
        if self.phase not in editable:
            raise ValueError(f"File edit not allowed in phase: {self.phase_label}")

    def check_plan_edit_path(self) -> None:
        """
        Confirm the edit targets the plan file (exact match or path-suffix).

        Raises:
            ValueError: If the path is not the configured plan file.

        Example:
            >>> # Raises ValueError when editing a non-plan file in plan-review:
            >>> guard.check_plan_edit_path()  # doctest: +SKIP
        """
        expected = self.config.plan_file_path
        if self.file_path != expected and not self.file_path.endswith(expected):
            raise ValueError(
                f"Editing '{self.file_path}' not allowed\nAllowed: {expected}"
            )

    def is_plan_file(self) -> bool:
        """True iff the target file is the configured plan file.

        Example:
            >>> guard.is_plan_file()  # doctest: +SKIP
            True
        """
        return path_matches(self.file_path, self.config.plan_file_path)

    def apply_edit_patch(self) -> str | None:
        """
        Simulate the Edit tool's old→new replacement against the on-disk file.

        Performs a single ``str.replace`` (replace count = 1) matching the
        behaviour of Claude Code's Edit tool, so the section-presence check
        runs against the *post-edit* content.

        Returns:
            str | None: Patched content, or ``None`` if the file does not
            exist (in which case there's nothing to validate).

        Example:
            >>> patched = guard.apply_edit_patch()  # doctest: +SKIP
        """
        from pathlib import Path

        path = Path(self.file_path)
        if not path.exists():
            return None

        current_content = path.read_text()
        tool_input = self.hook_input.get("tool_input", {})
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        # Single-replace matches Claude Code's Edit tool semantics (first match only).
        return current_content.replace(old_string, new_string, 1)

    def check_required_sections_present(self, content: str) -> None:
        """
        Ensure ``content`` still contains every required plan section.

        Args:
            content (str): Post-edit content to scan.

        Raises:
            ValueError: If any required section heading is missing.

        Example:
            >>> # Raises ValueError if the patched content drops a required section:
            >>> guard.check_required_sections_present("# only a header")  # doctest: +SKIP
        """
        ok, diff = template_conformance_check(content, DEFAULT_PLAN_TEMPLATE)
        if not ok:
            raise ValueError(f"Edit would remove required sections: {diff}")

    def check_plan_edit_preserves_sections(self) -> None:
        """Run the section-preservation check only when editing the plan file.

        Example:
            >>> guard.check_plan_edit_preserves_sections()  # doctest: +SKIP
        """
        if not self.is_plan_file():
            return
        patched = self.apply_edit_patch()
        # Non-existent file → nothing to check; defer error to Edit tool itself.
        if patched is None:
            return
        self.check_required_sections_present(patched)

    # ── Phase dispatch ────────────────────────────────────────────

    def validate_plan(self) -> None:
        """Apply plan-phase edit checks: path + section preservation.

        Example:
            >>> guard.validate_plan()  # doctest: +SKIP
        """
        self.check_plan_edit_path()
        self.check_plan_edit_preserves_sections()

    def validate(self) -> Decision:
        """
        Run the appropriate edit checks for the current phase.

        Returns:
            Decision: ``("allow", message)`` if the edit is permitted,
            otherwise ``("block", reason)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        try:
            # Test-mode short-circuits run before phase checks so fixtures can
            # touch the E2E report / state file regardless of workflow state.
            if self.is_test_report():
                return "allow", "E2E test report edit allowed (test mode)"

            if self.is_state_file():
                return "allow", "State file edit allowed (test mode)"

            self.check_editable_phase()

            if self.phase == "plan":
                self.validate_plan()

            return "allow", f"File edit allowed in phase: {self.phase}"
        except ValueError as e:
            return "block", str(e)
