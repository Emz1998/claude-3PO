"""FileEditGuard — Validates file edits against phase and path restrictions."""

from typing import Literal

from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]

from .write_guard import _is_e2e_report_path


class FileEditGuard:
    """Validate file edit against phase and path restrictions."""

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.file_path = hook_input.get("tool_input", {}).get("file_path", "")

    # ── Checks ────────────────────────────────────────────────────

    def _is_test_report(self) -> bool:
        return bool(self.state.get("test_mode")) and _is_e2e_report_path(self.file_path)

    def _is_state_file(self) -> bool:
        return self.state.get("test_mode") and self.file_path.endswith("state.jsonl")

    @property
    def _phase_label(self) -> str:
        return self.phase or "(no phase active — workflow not started)"

    def _check_editable_phase(self) -> None:
        editable = self.config.code_edit_phases + self.config.docs_edit_phases
        if self.phase not in editable:
            raise ValueError(f"File edit not allowed in phase: {self._phase_label}")

    def _check_plan_edit_path(self) -> None:
        expected = self.config.plan_file_path
        if self.file_path != expected and not self.file_path.endswith(expected):
            raise ValueError(
                f"Editing '{self.file_path}' not allowed\nAllowed: {expected}"
            )

    def _is_plan_file(self) -> bool:
        plan_path = self.config.plan_file_path
        return self.file_path == plan_path or self.file_path.endswith(plan_path)

    def _apply_edit_patch(self) -> str | None:
        """Return patched content after applying the edit, or None if file missing."""
        from pathlib import Path

        path = Path(self.file_path)
        if not path.exists():
            return None

        current_content = path.read_text()
        tool_input = self.hook_input.get("tool_input", {})
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        return current_content.replace(old_string, new_string, 1)

    def _check_required_sections_present(self, content: str) -> None:
        workflow_type = self.state.get("workflow_type", "build")
        required = self.config.get_plan_required_sections(workflow_type)
        missing = [s for s in required if s not in content]
        if missing:
            raise ValueError(f"Edit would remove required sections: {missing}")

    def _check_plan_edit_preserves_sections(self) -> None:
        if not self._is_plan_file():
            return
        patched = self._apply_edit_patch()
        if patched is None:
            return
        self._check_required_sections_present(patched)

    def _check_test_edit_path(self) -> None:
        allowed = self.state.tests.get("file_paths", [])
        if self.file_path not in allowed:
            raise ValueError(
                f"Editing '{self.file_path}' not allowed\nTest files in session: {allowed}"
            )

    @staticmethod
    def _basenames(paths: list[str]) -> set:
        return {p.rsplit("/", 1)[-1] for p in paths}

    def _all_code_tests_revised(self) -> bool:
        to_revise = self.state.code_tests_to_revise
        revised = self.state.code_tests_revised
        return bool(to_revise) and not (
            self._basenames(to_revise) - self._basenames(revised)
        )

    def _check_code_edit_path(self) -> None:
        test_files = self.state.tests.get("file_paths", [])
        code_files = self.state.code_files.get("file_paths", [])

        if self.file_path in test_files:
            return

        if self.file_path in code_files:
            if self.state.code_tests_to_revise and not self._all_code_tests_revised():
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

    def _validate_plan_review(self) -> None:
        self._check_plan_edit_path()
        self._check_plan_edit_preserves_sections()

    def _validate_test_review(self) -> None:
        self._check_test_edit_path()

    def _validate_code_review(self) -> None:
        self._check_code_edit_path()

    def validate(self) -> Decision:
        """Returns ("allow", message) or ("block", reason)."""
        try:
            if self._is_test_report():
                return "allow", "E2E test report edit allowed (test mode)"

            if self._is_state_file():
                return "allow", "State file edit allowed (test mode)"

            self._check_editable_phase()

            if self.phase == "plan-review":
                self._validate_plan_review()
            elif self.phase in ("test-review", "tests-review"):
                self._validate_test_review()
            elif self.phase == "code-review":
                self._validate_code_review()

            return "allow", f"File edit allowed in phase: {self.phase}"
        except ValueError as e:
            return "block", str(e)
