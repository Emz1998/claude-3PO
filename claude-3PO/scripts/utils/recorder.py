"""Recorder — flat 19-method API that wraps ``StateStore``.

Each ``record_*`` method is a thin wrapper: it builds the appropriate
data class (or nothing at all) and delegates to the matching
:class:`StateStore` method. All mutation logic lives on the store; this
class only chooses which store method to call for a given workflow
concept.

A ``record(hook_input, config)`` facade keeps ``post_tool_use.py`` on a
single entry point by routing Skill / Write / Edit / Bash events onto
the 19 methods.
"""

from typing import Literal

from lib.extractors import extract_skill_name
from lib.state_store import StateStore
from models.state import CodeReview, Task, TestReview, Validation
from config import Config


ListOp = tuple[Literal["add", "replace"], list[str]]


class Recorder:
    """Thin wrapper over :class:`StateStore` exposing 19 ``record_*`` methods.

    Every method builds a small data class (or nothing) and forwards to a
    matching state-store method. There is no mutation logic here — that
    lives on the store.

    Example:
        >>> Recorder(state).record_command("pytest")  # doctest: +SKIP
    """

    def __init__(self, state: StateStore) -> None:
        """Bind the recorder to a session state store.

        Args:
            state (StateStore): Session-scoped state to mutate.

        Example:
            >>> Recorder(state)  # doctest: +SKIP
        """
        self.state = state

    def _apply_op(self, op: ListOp | None, add_fn, set_fn) -> None:
        """Route a ``ListOp`` to the matching store add/replace method.

        Args:
            op (ListOp | None): ``("add", xs)`` or ``("replace", xs)``; noop if None.
            add_fn: Callable taking a single value — invoked per item on add.
            set_fn: Callable taking the full list — invoked on replace.

        Example:
            >>> self._apply_op(("add", ["a"]), self.state.add_test_file, self.state.set_test_file_paths)  # doctest: +SKIP
        """
        if op is None:
            return
        action, values = op
        if action == "replace":
            set_fn(list(values))
        else:
            for v in values:
                add_fn(v)

    # ── Artifacts ─────────────────────────────────────────────────

    def record_plan(
        self,
        file_path: str | None = None,
        written: bool | None = None,
        revised: bool | None = None,
        reviews: list[dict] | None = None,
    ) -> None:
        """Partial-update the plan artifact via store setters.

        Args:
            file_path (str | None): Where the plan was written.
            written (bool | None): Plan-written flag.
            revised (bool | None): Plan-revised flag.
            reviews (list[dict] | None): Replacement plan-review records.

        Example:
            >>> Recorder(state).record_plan(written=True)  # doctest: +SKIP
        """
        if file_path is not None:
            self.state.set_plan_file_path(file_path)
        if written is not None:
            self.state.set_plan_written(written)
        if revised is not None:
            self.state.set_plan_revised(revised)
        if reviews is not None:
            self.state.set_plan_reviews(reviews)

    def record_tests(
        self,
        file_paths: ListOp | None = None,
        executed: bool | None = None,
        reviews: list[dict] | None = None,
        files_to_revise: ListOp | None = None,
        files_revised: ListOp | None = None,
    ) -> None:
        """Partial-update the tests artifact via store setters.

        Args:
            file_paths (ListOp | None): Add/replace op for ``tests.file_paths``.
            executed (bool | None): Tests-executed flag.
            reviews (list[dict] | None): Replacement test-review records.
            files_to_revise (ListOp | None): Add/replace op for the to-revise list.
            files_revised (ListOp | None): Add/replace op for the revised list.

        Example:
            >>> Recorder(state).record_tests(executed=True)  # doctest: +SKIP
        """
        self._apply_op(file_paths, self.state.add_test_file, self.state.set_test_file_paths)
        if executed is not None:
            self.state.set_tests_executed(executed)
        if reviews is not None:
            self.state.set_test_reviews(reviews)
        self._apply_op(files_to_revise, self.state.add_test_file_to_revise, self.state.set_test_files_to_revise)
        self._apply_op(files_revised, self.state.add_test_file_revised, self.state.set_test_files_revised)

    def record_code_files(
        self,
        file_paths: ListOp | None = None,
        reviews: list[dict] | None = None,
        files_to_revise: ListOp | None = None,
        files_revised: ListOp | None = None,
    ) -> None:
        """Partial-update the code_files artifact via store setters.

        Args:
            file_paths (ListOp | None): Add/replace op for ``code_files.file_paths``.
            reviews (list[dict] | None): Replacement code-review records.
            files_to_revise (ListOp | None): Add/replace op for the to-revise list.
            files_revised (ListOp | None): Add/replace op for the revised list.

        Example:
            >>> Recorder(state).record_code_files(file_paths=("add", ["a.py"]))  # doctest: +SKIP
        """
        self._apply_op(file_paths, self.state.add_code_file, self.state.set_code_file_paths)
        if reviews is not None:
            self.state.set_code_reviews(reviews)
        self._apply_op(files_to_revise, self.state.add_code_file_to_revise, self.state.set_files_to_revise)
        self._apply_op(files_revised, self.state.add_file_revised, self.state.set_code_files_revised)

    def record_report_written(
        self, file_path: str | None = None, written: bool | None = None
    ) -> None:
        """Partial-update report_file_path and/or report_written.

        Args:
            file_path (str | None): Path of the final workflow report.
            written (bool | None): Report-written flag.

        Example:
            >>> Recorder(state).record_report_written(written=True)  # doctest: +SKIP
        """
        if file_path is not None:
            self.state.set_report_file_path(file_path)
        if written is not None:
            self.state.set_report_written(written)

    # ── Session / workflow metadata ───────────────────────────────

    def record_command(self, command: str) -> None:
        """Append ``command`` to ``state.commands``.

        Args:
            command (str): Bash command that just ran.

        Example:
            >>> Recorder(state).record_command("pytest")  # doctest: +SKIP
        """
        self.state.add_command(command)

    def record_session_id(self, session_id: str) -> None:
        """Set ``state.session_id``.

        Args:
            session_id (str): Session identifier.

        Example:
            >>> Recorder(state).record_session_id("sess-1")  # doctest: +SKIP
        """
        self.state.set("session_id", session_id)

    def record_story_id(self, story_id: str) -> None:
        """Set ``state.story_id``.

        Args:
            story_id (str): Story identifier.

        Example:
            >>> Recorder(state).record_story_id("US-1")  # doctest: +SKIP
        """
        self.state.set("story_id", story_id)

    def record_workflow_type(self, workflow_type: str) -> None:
        """Set ``state.workflow_type``.

        Args:
            workflow_type (str): One of ``build``/``implement``/``specs``/``ship``.

        Example:
            >>> Recorder(state).record_workflow_type("implement")  # doctest: +SKIP
        """
        self.state.set("workflow_type", workflow_type)

    def record_workflow_active(self, active: bool) -> None:
        """Set ``state.workflow_active``.

        Args:
            active (bool): Whether the workflow is live.

        Example:
            >>> Recorder(state).record_workflow_active(False)  # doctest: +SKIP
        """
        self.state.set("workflow_active", active)

    def record_workflow_status(
        self, status: Literal["in_progress", "completed"]
    ) -> None:
        """Set ``state.status``.

        Args:
            status (Literal): ``in_progress`` or ``completed``.

        Example:
            >>> Recorder(state).record_workflow_status("completed")  # doctest: +SKIP
        """
        self.state.set("status", status)

    def record_workflow(
        self,
        type: str | None = None,
        active: bool | None = None,
        status: Literal["in_progress", "completed"] | None = None,
    ) -> None:
        """Convenience: partial-update any of type/active/status.

        Args:
            type (str | None): Workflow type.
            active (bool | None): Active flag.
            status (Literal | None): Workflow status.

        Example:
            >>> Recorder(state).record_workflow(status="completed")  # doctest: +SKIP
        """
        if type is not None:
            self.record_workflow_type(type)
        if active is not None:
            self.record_workflow_active(active)
        if status is not None:
            self.record_workflow_status(status)

    # ── Lifecycle / flags ─────────────────────────────────────────

    def record_test_mode(self, test_mode: str) -> None:
        """Set ``state.test_mode``.

        Args:
            test_mode (str): Test-mode identifier.

        Example:
            >>> Recorder(state).record_test_mode("e2e")  # doctest: +SKIP
        """
        self.state.set_test_mode(test_mode)

    def record_phase(
        self,
        name: str,
        status: Literal["in_progress", "completed", "skipped"] = "in_progress",
    ) -> None:
        """Append a new phase entry to ``state.phases``.

        Args:
            name (str): Phase name.
            status (Literal): Phase status; defaults to ``in_progress``.

        Example:
            >>> Recorder(state).record_phase("plan")  # doctest: +SKIP
        """
        self.state.add_phase(name, status=status)

    def record_tdd(self, tdd: bool) -> None:
        """Set ``state.tdd``.

        Args:
            tdd (bool): TDD flag.

        Example:
            >>> Recorder(state).record_tdd(True)  # doctest: +SKIP
        """
        self.state.set_tdd(tdd)

    def record_validation_result(self, result: Literal["pass", "fail"]) -> None:
        """Append a :class:`Validation` record to ``state.validations``.

        Args:
            result (Literal): ``"pass"`` or ``"fail"``.

        Example:
            >>> Recorder(state).record_validation_result("pass")  # doctest: +SKIP
        """
        self.state.add_validation(Validation(result=result))

    # ── Agents / reviews / tasks ──────────────────────────────────

    def record_agent(
        self,
        name: str,
        status: Literal["in_progress", "completed", "failed"],
        tool_use_id: str,
    ) -> None:
        """Append an :class:`Agent` to ``state.agents``.

        Args:
            name (str): Subagent name.
            status (Literal): Current status.
            tool_use_id (str): Correlation id.

        Example:
            >>> Recorder(state).record_agent("Plan", "in_progress", "tu_1")  # doctest: +SKIP
        """
        from models.state import Agent
        self.state.add_agent(
            Agent(name=name, status=status, tool_use_id=tool_use_id)
        )

    def record_code_review(
        self,
        iteration: int,
        scores: dict,
        status=None,
    ) -> None:
        """Append a :class:`CodeReview` to ``code_files.reviews``.

        Args:
            iteration (int): Review iteration index.
            scores (dict): Score block.
            status (ReviewResult | None): Pass/Fail verdict if known.

        Example:
            >>> Recorder(state).record_code_review(1, {"c": 95}, "Pass")  # doctest: +SKIP
        """
        self.state.add_code_review_record(
            CodeReview(iteration=iteration, scores=scores, status=status)
        )

    def record_test_review(
        self,
        iteration: int,
        verdict,
        status=None,
    ) -> None:
        """Append a :class:`TestReview` to ``tests.reviews``.

        Args:
            iteration (int): Review iteration index.
            verdict (ReviewResult): Pass/Fail verdict.
            status (ReviewResult | None): Optional status label.

        Example:
            >>> Recorder(state).record_test_review(1, "Pass")  # doctest: +SKIP
        """
        self.state.add_test_review_record(
            TestReview(iteration=iteration, verdict=verdict, status=status)
        )

    def record_task(
        self,
        task_id: str,
        subject: str,
        description: str,
        parent_task_id: str | None = None,
    ) -> None:
        """Append a :class:`Task` to ``state.implement.project_tasks`` (dedup by task_id).

        Args:
            task_id (str): Task identifier.
            subject (str): Task subject.
            description (str): Task description.
            parent_task_id (str | None): Parent id if this is a subtask.

        Example:
            >>> Recorder(state).record_task("T-1", "s", "d")  # doctest: +SKIP
        """
        self.state.implement.add_project_task(
            Task(task_id=task_id, subject=subject,
                 description=description, parent_task_id=parent_task_id)
        )

    # ── Facade (not counted toward the 19) ────────────────────────

    def record(self, hook_input: dict, config: Config) -> None:
        """Thin PostToolUse dispatch onto the 19-method API.

        Skill → :meth:`record_phase`; Write/Edit → artifact methods keyed
        by the current phase; Bash → :meth:`record_command`. Unknown tools
        are ignored so the recorder never blocks a session.

        Args:
            hook_input (dict): PostToolUse payload.
            config (Config): Runtime configuration.

        Example:
            >>> Recorder(state).record({"tool_name": "Skill"}, config)  # doctest: +SKIP
        """
        handler = self._TOOL_RECORDERS.get(hook_input.get("tool_name", ""))
        if handler:
            handler(self, hook_input, config)

    def _dispatch_skill(self, hook_input: dict, _config: Config) -> None:
        """Route a Skill event to :meth:`record_phase`."""
        skill = extract_skill_name(hook_input)
        if skill:
            self.record_phase(skill)

    def _dispatch_write(self, hook_input: dict, config: Config) -> None:
        """Route a Write event to the artifact method for the current phase."""
        file_path = hook_input.get("tool_input", {}).get("file_path", "")
        phase = self.state.current_phase
        if phase == "plan":
            if file_path and file_path.endswith(config.plan_file_path):
                self.record_plan(file_path=file_path, written=True)
        elif phase == "write-tests":
            self.record_tests(file_paths=("add", [file_path]))
        elif phase == "write-code":
            self.record_code_files(file_paths=("add", [file_path]))
        elif phase == "write-report":
            self.record_report_written(file_path=file_path, written=True)

    def _dispatch_edit(self, hook_input: dict, _config: Config) -> None:
        """Route an Edit event to the revision method for the current phase."""
        file_path = hook_input.get("tool_input", {}).get("file_path", "")
        phase = self.state.current_phase
        if phase == "plan-review":
            self.record_plan(revised=True)
        elif phase == "test-review" and file_path:
            self.record_tests(files_revised=("add", [file_path]))
        elif phase == "code-review" and file_path:
            self.record_code_files(files_revised=("add", [file_path]))

    def _dispatch_bash(self, hook_input: dict, _config: Config) -> None:
        """Route a Bash event to :meth:`record_command`."""
        command = hook_input.get("tool_input", {}).get("command", "")
        if command:
            self.record_command(command)

    _TOOL_RECORDERS: dict = {
        "Skill": _dispatch_skill,
        "Write": _dispatch_write,
        "Edit": _dispatch_edit,
        "Bash": _dispatch_bash,
    }
