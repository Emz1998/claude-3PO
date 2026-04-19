"""FileEditGuard — Validates file edits against phase and path restrictions."""

from typing import Literal

from lib.state_store import StateStore
from lib.paths import all_revised, is_e2e_report_path, path_matches
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class FileEditGuard:
    """Validate an Edit tool call against the current phase + path rules.

    The edit phases are tightly scoped:

    - ``plan-review`` — only the plan file may be edited, and the edit must not
      remove any of the plan's required sections (the guard simulates the patch
      and checks the post-edit content).
    - ``test-review`` / ``tests-review`` — only test files registered for this
      session.
    - ``code-review`` — registered code files, and only after all flagged tests
      have been revised first.

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
            'plan-review'
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
        workflow_type = self.state.get("workflow_type", "build")
        required = self.config.get_plan_required_sections(workflow_type)
        missing = [s for s in required if s not in content]
        if missing:
            raise ValueError(f"Edit would remove required sections: {missing}")

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

    def check_test_edit_path(self) -> None:
        """
        Confirm the edit targets a test file registered for this session.

        Raises:
            ValueError: If the path is not in ``state.tests.file_paths``.

        Example:
            >>> # Raises ValueError when editing a test file not registered in state:
            >>> guard.check_test_edit_path()  # doctest: +SKIP
        """
        allowed = self.state.tests.get("file_paths", [])
        if self.file_path not in allowed:
            raise ValueError(
                f"Editing '{self.file_path}' not allowed\nTest files in session: {allowed}"
            )

    def check_code_edit_path(self) -> None:
        """
        Confirm a code-review edit is on a registered file and tests are revised.

        Editing test files is always fine (they're registered separately). Editing
        code files requires that any flagged code-tests have already been revised
        — the guard refuses to let production code change while its tests still
        need updating.

        Raises:
            ValueError: If the path isn't a registered test/code file, or if
                code-tests still need revision.

        Example:
            >>> # Raises ValueError when tests still need to be revised first:
            >>> guard.check_code_edit_path()  # doctest: +SKIP
        """
        test_files = self.state.tests.get("file_paths", [])
        code_files = self.state.code_files.get("file_paths", [])

        # Test-file edits are always allowed during code-review — they're part
        # of the review-revise loop on their own track.
        if self.file_path in test_files:
            return

        if self.file_path in code_files:
            if self.state.code_tests_to_revise and not all_revised(
                self.state.code_tests_to_revise, self.state.code_tests_revised
            ):
                raise ValueError(
                    "Revise test files first before editing code files"
                    f"\nTests to revise: {self.state.code_tests_to_revise}"
                    f"\nTests revised: {self.state.code_tests_revised}"
                )
            return

        raise ValueError(
            f"Editing '{self.file_path}' not allowed\nCode files in session: {code_files}"
        )

    # ── Phase dispatch ────────────────────────────────────────────

    def validate_plan_review(self) -> None:
        """Apply plan-review edit checks: path + section preservation.

        Example:
            >>> guard.validate_plan_review()  # doctest: +SKIP
        """
        self.check_plan_edit_path()
        self.check_plan_edit_preserves_sections()

    def validate_test_review(self) -> None:
        """Apply test-review edit checks: path must be a registered test file.

        Example:
            >>> guard.validate_test_review()  # doctest: +SKIP
        """
        self.check_test_edit_path()

    def validate_code_review(self) -> None:
        """Apply code-review edit checks: path + tests-revised gating.

        Example:
            >>> guard.validate_code_review()  # doctest: +SKIP
        """
        self.check_code_edit_path()

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

            if self.phase == "plan-review":
                self.validate_plan_review()
            elif self.phase in ("test-review", "tests-review"):
                self.validate_test_review()
            elif self.phase == "code-review":
                self.validate_code_review()

            return "allow", f"File edit allowed in phase: {self.phase}"
        except ValueError as e:
            return "block", str(e)
