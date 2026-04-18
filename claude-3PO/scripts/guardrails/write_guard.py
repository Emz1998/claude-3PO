"""FileWriteGuard — Validates file writes against phase and path restrictions."""

from fnmatch import fnmatch

from constants import (
    TEST_FILE_PATTERNS,
    CODE_EXTENSIONS,
)
from constants.paths import E2E_TEST_REPORT
from typing import Literal

from lib.state_store import StateStore
from lib.extractors import extract_md_sections
from lib.paths import path_matches
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def _is_e2e_report_path(file_path: str) -> bool:
    """
    Check whether a path refers to the E2E test report.

    Matches any top-level ``E2E*_TEST_REPORT.md`` filename (so per-suite reports
    like ``E2E_BUILD_TEST_REPORT.md`` all qualify) and the legacy
    ``.claude/reports`` path retained for back-compat.

    Args:
        file_path (str): Candidate file path.

    Returns:
        bool: ``True`` when the path matches one of the recognised E2E forms.

    Example:
        >>> _is_e2e_report_path("E2E_BUILD_TEST_REPORT.md")
        True
    """
    if not file_path:
        return False
    basename = file_path.rsplit("/", 1)[-1]
    if basename.startswith("E2E") and basename.endswith("_TEST_REPORT.md"):
        return True
    return file_path == E2E_TEST_REPORT or file_path.endswith(E2E_TEST_REPORT)


class FileWriteGuard:
    """Validate a Write tool call against the current phase + path rules.

    Each writable phase has its own per-path-and-content validator:

    - ``plan`` — only the plan file; plan content must contain every required
      section (and bullet sections must use bullets, not H3 subsections).
    - ``write-tests`` — only paths matching ``TEST_FILE_PATTERNS``.
    - ``write-code`` — code-extension paths (build) or paths from the plan's
      ``## Files to Create/Modify`` (implement).
    - ``write-report`` — only the configured report file path.

    Test-mode shortcut: writes to the E2E test report or ``state.jsonl`` are
    always allowed when ``state.test_mode`` is set.

    Example:
        >>> guard = FileWriteGuard(hook_input, config, state)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        """
        Cache the target path, content, and dependencies.

        Args:
            hook_input (dict): Raw PreToolUse hook payload.
            config (Config): Workflow configuration.
            state (StateStore): Mutable workflow state snapshot.

        Example:
            >>> guard = FileWriteGuard(hook_input, config, state)  # doctest: +SKIP
            >>> guard.file_path  # doctest: +SKIP
            'plan.md'
        """
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.file_path = hook_input.get("tool_input", {}).get("file_path", "")
        self.content = hook_input.get("tool_input", {}).get("content", "")

    # ── Test mode ─────────────────────────────────────────────────

    def _is_test_report(self) -> bool:
        """True iff in test mode and the path is an E2E test report.

        Example:
            >>> guard._is_test_report()  # doctest: +SKIP
            True
        """
        return bool(self.state.get("test_mode")) and _is_e2e_report_path(self.file_path)

    def _is_state_file(self) -> bool:
        """True iff in test mode and the path ends with ``state.jsonl``.

        Example:
            >>> guard._is_state_file()  # doctest: +SKIP
            True
        """
        return self.state.get("test_mode") and self.file_path.endswith("state.jsonl")

    # ── Phase check ───────────────────────────────────────────────

    @property
    def _phase_label(self) -> str:
        """Human-readable phase name, or a placeholder when no phase is active.

        Example:
            >>> guard._phase_label  # doctest: +SKIP
            'plan'
        """
        return self.phase or "(no phase active — workflow not started)"

    def _check_writable_phase(self) -> None:
        """
        Reject writes when the current phase isn't a write-capable phase.

        Raises:
            ValueError: If the phase isn't in ``code_write_phases`` or
                ``docs_write_phases``.

        Example:
            >>> # Raises ValueError when the current phase doesn't permit writes:
            >>> guard._check_writable_phase()  # doctest: +SKIP
        """
        writable = self.config.code_write_phases + self.config.docs_write_phases
        if self.phase not in writable:
            raise ValueError(f"File write not allowed in phase: {self._phase_label}")

    # ── Plan phase ────────────────────────────────────────────────

    def _check_agent_completed(self, agent_name: str) -> None:
        """
        Require the named agent to have run at least once and finished.

        Args:
            agent_name (str): Agent name to check (e.g. ``"Plan"``).

        Raises:
            ValueError: If the agent never ran or any invocation isn't completed.

        Example:
            >>> # Raises ValueError when the agent hasn't been invoked yet:
            >>> guard._check_agent_completed("Plan")  # doctest: +SKIP
        """
        agents = [a for a in self.state.agents if a.get("name") == agent_name]
        if not agents:
            raise ValueError(f"{agent_name} agent must be invoked first")
        if not all(a.get("status") == "completed" for a in agents):
            raise ValueError(f"{agent_name} agent must complete before writing")

    def _check_plan_path(self) -> None:
        """
        Confirm the write targets the plan file.

        Raises:
            ValueError: If the path isn't the configured plan file.

        Example:
            >>> # Raises ValueError when writing a non-plan path during plan phase:
            >>> guard._check_plan_path()  # doctest: +SKIP
        """
        expected = self.config.plan_file_path
        if not (expected and (self.file_path == expected or self.file_path.endswith(expected))):
            raise ValueError(
                f"Writing '{self.file_path}' not allowed\nAllowed: {expected}"
            )

    def _is_plan_file(self) -> bool:
        """True iff the target file is the configured plan file.

        Example:
            >>> guard._is_plan_file()  # doctest: +SKIP
            True
        """
        return path_matches(self.file_path, self.config.plan_file_path)

    def _check_plan_content(self) -> None:
        """Dispatch to the build- or implement-flavour plan-content check.

        Example:
            >>> guard._check_plan_content()  # doctest: +SKIP
        """
        workflow_type = self.state.get("workflow_type", "build")
        if workflow_type == "implement":
            self._check_implement_plan_sections()
        else:
            self._check_build_plan_sections()

    def _check_build_plan_sections(self) -> None:
        """
        Ensure a build-workflow plan has all required sections and bullet sections.

        Raises:
            ValueError: If a required section heading is missing or a
                bullet section uses ``###`` subsections / no bullets.

        Example:
            >>> # Raises ValueError when required sections are missing from plan content:
            >>> guard._check_build_plan_sections()  # doctest: +SKIP
        """
        required = self.config.build_plan_required_sections
        missing = [s for s in required if s not in self.content]
        if missing:
            raise ValueError(f"Plan missing required sections: {missing}")
        section_map = {
            name.strip(): body for name, body in extract_md_sections(self.content, 2)
        }
        for section_name in self.config.build_plan_bullet_sections:
            self._check_bullet_section(section_name, section_map.get(section_name, ""))

    @staticmethod
    def _check_bullet_section(section_name: str, body: str) -> None:
        """
        Enforce that a section uses ``- item`` bullets (no ``###`` subsections).

        Args:
            section_name (str): Heading of the section being checked.
            body (str): Markdown body of the section.

        Raises:
            ValueError: If ``###`` subsections appear or no bullet items exist.

        Example:
            >>> # Returns None when the body uses bullets:
            >>> FileWriteGuard._check_bullet_section("Tasks", "- one\\n- two")
            >>> # Raises ValueError when the body has no bullets or uses ### subsections.
        """
        if "### " in body:
            raise ValueError(
                f"'{section_name}' must use bullet items (- item), not ### subsections. "
                f"See the plan template for the correct format."
            )
        if not any(line.strip().startswith("- ") for line in body.splitlines()):
            raise ValueError(
                f"'{section_name}' must have at least one bullet item (- item). "
                f"See the plan template for the correct format."
            )

    def _check_implement_plan_sections(self) -> None:
        """
        Ensure an implement-workflow plan has all required sections.

        Raises:
            ValueError: If any required section heading is missing.

        Example:
            >>> # Raises ValueError when required sections are missing:
            >>> guard._check_implement_plan_sections()  # doctest: +SKIP
        """
        required = self.config.implement_plan_required_sections
        missing = [s for s in required if s not in self.content]
        if missing:
            raise ValueError(f"Plan missing required sections: {missing}")

    def _validate_plan(self) -> None:
        """Apply plan-phase write checks: agent done, path, plan content.

        Example:
            >>> guard._validate_plan()  # doctest: +SKIP
        """
        self._check_agent_completed("Plan")
        self._check_plan_path()
        if self._is_plan_file():
            self._check_plan_content()

    # ── Other phases ──────────────────────────────────────────────

    def _check_test_path(self) -> None:
        """
        Restrict ``write-tests`` writes to filenames matching test patterns.

        Raises:
            ValueError: If the basename matches no entry in ``TEST_FILE_PATTERNS``.

        Example:
            >>> # Raises ValueError when the file doesn't match a test-file pattern:
            >>> guard._check_test_path()  # doctest: +SKIP
        """
        basename = self.file_path.rsplit("/", 1)[-1]
        if not any(fnmatch(basename, p) for p in TEST_FILE_PATTERNS):
            raise ValueError(
                f"Writing '{self.file_path}' not allowed"
                f"\nAllowed patterns: {TEST_FILE_PATTERNS}"
            )

    def _check_code_path(self) -> None:
        """
        Restrict generic code writes to recognised code-file extensions.

        Raises:
            ValueError: If the path doesn't end with any ``CODE_EXTENSIONS`` suffix.

        Example:
            >>> # Raises ValueError when path doesn't end in a recognised code extension:
            >>> guard._check_code_path()  # doctest: +SKIP
        """
        if not any(self.file_path.endswith(ext) for ext in CODE_EXTENSIONS):
            raise ValueError(
                f"Writing '{self.file_path}' not allowed"
                f"\nAllowed extensions: {CODE_EXTENSIONS}"
            )

    def _check_implement_code_path(self) -> None:
        """
        Restrict implement-workflow code writes to plan's declared file list.

        Raises:
            ValueError: If the path isn't listed in the plan's
                ``## Files to Create/Modify`` section.

        Example:
            >>> # Raises ValueError when path isn't in the plan's modify list:
            >>> guard._check_implement_code_path()  # doctest: +SKIP
        """
        allowed = self.state.implement.plan_files_to_modify
        if self.file_path not in allowed:
            raise ValueError(
                f"Writing '{self.file_path}' not in plan's ## Files to Create/Modify"
                f"\nAllowed: {allowed}"
            )

    def _check_report_path(self) -> None:
        """
        Restrict ``write-report`` writes to the configured report file path.

        Raises:
            ValueError: If the path doesn't match the configured report path.

        Example:
            >>> # Raises ValueError when path doesn't match the configured report path:
            >>> guard._check_report_path()  # doctest: +SKIP
        """
        expected = self.config.report_file_path
        if not path_matches(self.file_path, expected):
            raise ValueError(
                f"Writing '{self.file_path}' not allowed\nAllowed: {expected}"
            )

    def _validate_write_code(self) -> None:
        """Dispatch to build- or implement-flavour code-path check.

        Example:
            >>> guard._validate_write_code()  # doctest: +SKIP
        """
        workflow_type = self.state.get("workflow_type", "build")
        if workflow_type == "implement":
            self._check_implement_code_path()
        else:
            self._check_code_path()

    # ── Phase dispatch ────────────────────────────────────────────

    def validate(self) -> Decision:
        """
        Run the appropriate write checks for the current phase.

        Returns:
            Decision: ``("allow", message)`` if the write is permitted,
            otherwise ``("block", reason)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        try:
            if self._is_test_report():
                return "allow", "E2E test report write allowed (test mode)"

            if self._is_state_file():
                return "allow", "State file write allowed (test mode)"

            self._check_writable_phase()

            if self.phase == "plan":
                self._validate_plan()
            elif self.phase == "write-tests":
                self._check_test_path()
            elif self.phase == "write-code":
                self._validate_write_code()
            elif self.phase == "write-report":
                self._check_report_path()

            return "allow", f"File write allowed in phase: {self.phase}"
        except ValueError as e:
            return "block", str(e)
