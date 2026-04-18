"""Recorder — Records state changes after successful tool use.

The Recorder is the *write-side* counterpart to the Resolver: guards
decide whether a tool use is allowed, the recorder mutates state to
reflect what was just done, and the resolver then evaluates whether the
phase is complete.

Dispatch is table-driven via ``TOOL_RECORDERS`` (one handler per Claude
tool name) and ``_PHASE_SKILL_HANDLERS`` (one handler per state-mutating
meta-skill). Adding a new tool or skill is a one-line table edit plus a
small handler — keeping recording logic out of long if/elif chains.
"""

import json
import re
from pathlib import Path

from constants import TEST_RUN_PATTERNS
from lib.extractors import (
    extract_skill_name,
    extract_scores,
    extract_verdict,
    extract_plan_tasks,
    extract_plan_files_to_modify,
)
from lib.parallel_check import is_parallel_explore_research
from lib.scoring import scores_valid, verdict_valid
from lib.state_store import StateStore
from lib.paths import basenames
from config import Config


_NO_TRANSITION_SKILLS = (
    "continue",
    "revise-plan",
    "plan-approved",
    "reset-plan-review",
)


class Recorder:
    """Records state changes after guards allow a tool use.

    Methods are grouped by what triggers them: phase transitions, bash
    commands, file writes, file edits, agent reports, and skill side
    effects. The terminal ``record()`` is the entry point used by the
    PostToolUse hook — everything else is callable individually so unit
    tests can exercise each branch without staging full hook payloads.

    Example:
        >>> Recorder(state)  # doctest: +SKIP
    """

    def __init__(self, state: StateStore):
        """Bind the recorder to a session state store.

        Args:
            state (StateStore): Session-scoped state to mutate.

        Example:
            >>> Recorder(state)  # doctest: +SKIP
        """
        self.state = state

    def _is_session_file(self, file_path: str) -> bool:
        """Return True iff ``file_path``'s basename is a tracked code/test file.

        Comparison is by basename so paths from different working directories
        (Edits sometimes report absolute, sometimes repo-relative) still match
        the entries written by Write events.

        Args:
            file_path (str): Path from a tool_input payload.

        Returns:
            bool: True if the file is one we track in this session.

        Example:
            >>> Recorder(state)._is_session_file("src/foo.py")  # doctest: +SKIP
        """
        code_files = self.state.code_files.get("file_paths", [])
        test_files = self.state.tests.get("file_paths", [])
        all_files = basenames(code_files + test_files)
        basename = file_path.rsplit("/", 1)[-1]
        return basename in all_files

    # ── Phase transition ──────────────────────────────────────────

    def record_phase_transition(
        self, current: str, next_phase: str, parallel: bool = False
    ) -> None:
        """Mark the current phase complete (if any) and start ``next_phase``.

        Skipped entirely for meta-skills in ``_NO_TRANSITION_SKILLS`` (e.g.
        ``/continue``) — those mutate state via different handlers and
        should not show up as their own phases. ``parallel=True`` keeps
        the current phase open so an in-flight phase (e.g. ``explore``)
        can run alongside the new one (e.g. ``research``).

        Args:
            current (str): Currently active phase name, or ``""`` if none.
            next_phase (str): Skill name that's starting.
            parallel (bool): If True, do not auto-complete ``current``.

        Example:
            >>> Recorder(state).record_phase_transition("plan", "write-code")  # doctest: +SKIP
        """
        if next_phase in _NO_TRANSITION_SKILLS:
            return
        if current and not parallel:
            self.state.set_phase_completed(current)
        self.state.add_phase(next_phase)

    # ── Command ───────────────────────────────────────────────────

    def record_test_execution(self, phase: str, command: str) -> None:
        """Flag tests as executed when a test-run command fires in a test phase.

        Args:
            phase (str): Currently active phase.
            command (str): The bash command that just ran.

        Example:
            >>> Recorder(state).record_test_execution("write-tests", "pytest")  # doctest: +SKIP
        """
        if phase in ("write-tests", "test-review"):
            if any(re.search(p, command) for p in TEST_RUN_PATTERNS):
                self.state.set_tests_executed(True)

    def record_pr_create(self, output: str) -> None:
        """Persist PR number/status from a ``gh pr create`` JSON output.

        Args:
            output (str): Raw stdout from ``gh pr create --json``.

        Raises:
            ValueError: If output isn't valid JSON or lacks a ``"number"`` field.

        Example:
            >>> Recorder(state).record_pr_create('{"number": 42}')  # doctest: +SKIP
        """
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse PR create output as JSON: {output}")
        number = data.get("number")
        if number is None:
            raise ValueError("PR create output missing 'number' field")
        self.state.set_pr_number(number)
        self.state.set_pr_status("created")

    def record_ci_check(self, output: str) -> None:
        """Persist CI results from a ``gh pr checks`` JSON output.

        Aggregates the per-check ``conclusion`` field into a single status:
        any ``FAILURE`` → failed; all ``SUCCESS`` → passed; otherwise pending.
        Pending is the default so a partially-reported run isn't prematurely
        treated as green.

        Args:
            output (str): Raw stdout from ``gh pr checks --json``. May be
                a top-level array or an object with a ``"checks"`` array.

        Raises:
            ValueError: If output isn't valid JSON.

        Example:
            >>> Recorder(state).record_ci_check('[{"conclusion": "SUCCESS"}]')  # doctest: +SKIP
        """
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse CI check output as JSON: {output}")
        results = data if isinstance(data, list) else data.get("checks", [])
        self.state.set_ci_results(results)
        if any(r.get("conclusion") == "FAILURE" for r in results):
            self.state.set_ci_status("failed")
        elif all(r.get("conclusion") == "SUCCESS" for r in results):
            self.state.set_ci_status("passed")
        else:
            self.state.set_ci_status("pending")

    # ── File write ────────────────────────────────────────────────

    _SPECS_DOC_PHASES: dict[str, str] = {"vision": "product_vision", "decision": "decisions"}

    def record_write(self, phase: str, file_path: str, is_plan_file: bool) -> None:
        """Route a Write tool event to the right phase-specific recorder.

        Args:
            phase (str): Currently active phase.
            file_path (str): Path that was written.
            is_plan_file (bool): True if ``file_path`` matches the configured
                plan path (computed by the caller).

        Example:
            >>> Recorder(state).record_write("write-code", "src/foo.py", False)  # doctest: +SKIP
        """
        if phase == "plan":
            self.record_plan_write(file_path, is_plan_file)
        elif phase == "write-tests":
            self.state.add_test_file(file_path)
        elif phase == "write-code":
            self.state.add_code_file(file_path)
        elif phase == "write-report":
            self.state.set_report_written(True)
        elif phase in self._SPECS_DOC_PHASES:
            self._record_specs_doc(self._SPECS_DOC_PHASES[phase], file_path)

    def record_plan_write(self, file_path: str, is_plan_file: bool) -> None:
        """Record a plan-file write only when the path matches the plan target.

        Example:
            >>> Recorder(state)._record_plan_write("plan.md", True)  # doctest: +SKIP
        """
        if is_plan_file:
            self.state.set_plan_file_path(file_path)
            self.state.set_plan_written(True)

    def _record_specs_doc(self, doc_key: str, file_path: str) -> None:
        """Mark a specs doc written and record its path under ``state.docs[doc_key]``.

        Example:
            >>> Recorder(state)._record_specs_doc("product_vision", "vision.md")  # doctest: +SKIP
        """
        self.state.set_doc_written(doc_key, True)
        self.state.set_doc_path(doc_key, file_path)

    def record_plan_metadata(self, file_path: str) -> None:
        """Inject auto-derived metadata (story id, dates, …) into the plan file.

        Args:
            file_path (str): Path to the just-written plan markdown.

        Example:
            >>> Recorder(state).record_plan_metadata("plan.md")  # doctest: +SKIP
        """
        from lib.injector import inject_plan_metadata
        inject_plan_metadata(file_path, self.state)

    def record_plan_sections(self, file_path: str) -> None:
        """Auto-parse Tasks and Files-to-Modify out of the plan.

        Reading both sections at once amortizes the file read; doing it as
        part of the plan-write recorder means downstream phases
        (create-tasks, write-code) can rely on these lists being populated
        without an extra parse step.

        Args:
            file_path (str): Path to the just-written plan markdown.

        Example:
            >>> Recorder(state).record_plan_sections("plan.md")  # doctest: +SKIP
        """
        path = Path(file_path)
        if not path.exists():
            return

        content = path.read_text()
        self.state.set_tasks(extract_plan_tasks(content))

        for f in extract_plan_files_to_modify(content):
            self.state.add_code_file_to_write(f)

    # ── File edit ─────────────────────────────────────────────────

    def record_edit(self, phase: str, file_path: str) -> None:
        """Record an Edit tool event as a revision in the relevant phase.

        For ``code-review``, files split into two buckets: those flagged for
        revision in the latest review (``code_tests_to_revise``) record as
        test revisions, others as code revisions — but only if they're
        already part of the session's tracked file set, to avoid recording
        unrelated edits Claude makes during review.

        Args:
            phase (str): Currently active phase.
            file_path (str): Path that was edited.

        Example:
            >>> Recorder(state).record_edit("plan-review", "plan.md")  # doctest: +SKIP
        """
        if phase == "plan-review":
            self.state.set_plan_revised(True)
        elif phase == "test-review" and file_path:
            self.state.add_test_file_revised(file_path)
        elif phase == "code-review" and file_path:
            basename = file_path.rsplit("/", 1)[-1]
            to_revise_basenames = basenames(self.state.code_tests_to_revise)
            if basename in to_revise_basenames:
                self.state.add_code_test_revised(file_path)
            elif self._is_session_file(file_path):
                self.state.add_file_revised(file_path)

    # ── Agent report ──────────────────────────────────────────────

    def record_scores(self, phase: str, content: str) -> None:
        """Pull confidence/quality scores out of a review report and append.

        Args:
            phase (str): One of ``plan-review`` / ``code-review``; ignored otherwise.
            content (str): Raw agent report text containing the score block.

        Example:
            >>> Recorder(state).record_scores("plan-review", "...scores...")  # doctest: +SKIP
        """
        if phase in ("plan-review", "code-review"):
            _, extracted = scores_valid(content, extract_scores)
            if phase == "plan-review":
                self.state.add_plan_review(extracted)
            else:
                self.state.add_code_review(extracted)

    def record_verdict(self, phase: str, content: str) -> None:
        """Pull a Pass/Fail verdict out of a review or check report.

        Args:
            phase (str): ``test-review``, ``quality-check``, or ``validate``;
                other phases are ignored.
            content (str): Raw agent report text containing the verdict line.

        Example:
            >>> Recorder(state).record_verdict("test-review", "Verdict: Pass")  # doctest: +SKIP
        """
        if phase == "test-review":
            _, verdict = verdict_valid(content, extract_verdict)
            self.state.add_test_review(verdict)

        if phase in ("quality-check", "validate"):
            _, verdict = verdict_valid(content, extract_verdict)
            self.state.set_quality_check_result(verdict)

    def record_revision_files(
        self, phase: str, files: list[str], tests: list[str]
    ) -> None:
        """Record which files a review flagged for revision.

        Args:
            phase (str): ``code-review`` or ``test-review`` (others ignored).
            files (list[str]): Files to revise.
            tests (list[str]): Tests to revise (only used by code-review).

        Example:
            >>> Recorder(state).record_revision_files("code-review", ["a.py"], [])  # doctest: +SKIP
        """
        if phase == "code-review" and files:
            self.state.set_files_to_revise(files)
            self.state.set_code_tests_to_revise(tests)
        elif phase == "test-review" and files:
            self.state.set_test_files_to_revise(files)

    # ── Specs report side-effects (moved from AgentReportGuard) ───

    _SPECS_AGENT_BY_PHASE = {"architect": "Architect", "backlog": "ProductOwner"}

    def write_specs_doc(self, phase: str, content: str, config: Config) -> None:
        """Write architect or backlog content to disk and record paths in state.

        Args:
            phase (str): ``architect`` or ``backlog``; other phases are no-ops.
            content (str): Markdown body produced by the agent.
            config (Config): Runtime config supplying destination paths.

        Example:
            >>> Recorder(state).write_specs_doc("architect", "# Arch", config)  # doctest: +SKIP
        """
        if phase == "architect":
            self._write_architecture(content, config)
        elif phase == "backlog":
            self._write_backlog(content, config)

    def _write_architecture(self, content: str, config: Config) -> None:
        """Persist architecture markdown and update ``state.docs.architecture``.

        Example:
            >>> Recorder(state)._write_architecture("# Arch", config)  # doctest: +SKIP
        """
        from utils.specs_writer import write_doc

        path = config.architecture_file_path
        write_doc(content, path)
        self.state.set_doc_written("architecture", True)
        self.state.set_doc_path("architecture", path)

    def _write_backlog(self, content: str, config: Config) -> None:
        """Persist backlog markdown + JSON and update ``state.docs.backlog``.

        Example:
            >>> Recorder(state)._write_backlog("# Backlog", config)  # doctest: +SKIP
        """
        from utils.specs_writer import write_backlog

        md_path = config.backlog_md_file_path
        json_path = config.backlog_json_file_path
        write_backlog(content, md_path, json_path)
        self.state.set_doc_written("backlog", True)
        self.state.set_doc_md_path("backlog", md_path)
        self.state.set_doc_json_path("backlog", json_path)

    def mark_specs_agent_failed(self, phase: str) -> None:
        """Mark the latest agent record for ``phase`` as failed.

        Args:
            phase (str): Specs phase whose agent should be flagged
                (architect → Architect; backlog → ProductOwner).

        Example:
            >>> Recorder(state).mark_specs_agent_failed("architect")  # doctest: +SKIP
        """
        agent_name = self._SPECS_AGENT_BY_PHASE.get(phase)
        if agent_name:
            self.state.mark_last_agent_failed(agent_name)

    # ── TaskCreated side-effects (moved from TaskCreatedGuard) ────

    def record_created_task(self, matched_subject: str) -> None:
        """Append a freshly-created task subject to the created-tasks list.

        Example:
            >>> Recorder(state).record_created_task("Implement login")  # doctest: +SKIP
        """
        self.state.add_created_task(matched_subject)

    def record_subtask(self, parent_id: str, payload: dict) -> None:
        """Attach a subtask payload under its parent project task.

        Args:
            parent_id (str): Project-task id that owns the subtask.
            payload (dict): Subtask data as recorded on the parent.

        Example:
            >>> Recorder(state).record_subtask("PT-1", {"title": "x"})  # doctest: +SKIP
        """
        self.state.add_subtask(parent_id, payload)

    # ── Skill side-effects (moved from PhaseGuard) ────────────────

    def apply_phase_skill(self, skill: str, current: str, status: str) -> None:
        """Mutate state for the meta-skills /continue, /plan-approved, /revise-plan.

        These three skills don't open their own phase entries — they
        instead nudge an existing phase (close it, re-open it, or jump
        the plan-review checkpoint). The dispatch table keeps the
        per-skill behaviour grouped at the bottom of the class for easy
        extension.

        Args:
            skill (str): Skill name from the SkillStart event.
            current (str): Currently active phase.
            status (str): Status of ``current`` (``in_progress`` or ``completed``).

        Example:
            >>> Recorder(state).apply_phase_skill("continue", "plan", "in_progress")  # doctest: +SKIP
        """
        handler = self._PHASE_SKILL_HANDLERS.get(skill)
        if handler is not None:
            handler(self, current, status)

    def _apply_continue(self, current: str, status: str) -> None:
        """``/continue`` — close the current in-progress phase.

        Example:
            >>> Recorder(state)._apply_continue("plan", "in_progress")  # doctest: +SKIP
        """
        if status == "in_progress":
            self.state.set_phase_completed(current)

    def _apply_plan_approved(self, current: str, status: str) -> None:
        """``/plan-approved`` — close ``plan-review`` even if not the current phase.

        Example:
            >>> Recorder(state)._apply_plan_approved("plan-review", "in_progress")  # doctest: +SKIP
        """
        if status == "in_progress":
            self.state.set_phase_completed("plan-review")

    def _apply_revise_plan(self, current: str, status: str) -> None:
        """``/revise-plan`` — re-open plan-review and clear prior reviews.

        Used when the user wants a fresh review pass after editing the
        plan. The reviews list is wiped (not just appended to) so the
        scoring resolver starts from a clean slate.

        Args:
            current (str): Currently active phase (unused — included for
                handler-signature uniformity).
            status (str): Phase status (unused, same reason).

        Example:
            >>> Recorder(state)._apply_revise_plan("plan-review", "completed")  # doctest: +SKIP
        """
        def _reopen(d: dict) -> None:
            for p in d.get("phases", []):
                if p["name"] == "plan-review":
                    p["status"] = "in_progress"
                    break
            plan = d.setdefault("plan", {})
            plan["revised"] = False
            plan["reviews"] = []

        self.state.update(_reopen)

    _PHASE_SKILL_HANDLERS: dict = {
        "continue": _apply_continue,
        "plan-approved": _apply_plan_approved,
        "revise-plan": _apply_revise_plan,
    }

    # ── Dispatch ──────────────────────────────────────────────────

    def _dispatch_edit(self, hook_input: dict, config: Config, phase: str) -> None:
        """Dispatch an Edit tool event to :meth:`record_edit`.

        Example:
            >>> Recorder(state)._dispatch_edit({"tool_input": {}}, config, "plan-review")  # doctest: +SKIP
        """
        self.record_edit(phase, hook_input.get("tool_input", {}).get("file_path", ""))

    def _dispatch_bash(self, hook_input: dict, config: Config, phase: str) -> None:
        """Dispatch a Bash tool event to the bash recorder.

        Example:
            >>> Recorder(state)._dispatch_bash({}, config, "write-tests")  # doctest: +SKIP
        """
        self._record_bash(
            hook_input.get("tool_input", {}), hook_input.get("tool_result", ""), phase
        )

    def _dispatch_skill(self, hook_input: dict, config: Config, phase: str) -> None:
        """Dispatch a Skill tool event to the skill recorder.

        Example:
            >>> Recorder(state)._dispatch_skill({}, config, "plan")  # doctest: +SKIP
        """
        self._record_skill(hook_input.get("tool_input", {}), phase)

    def _dispatch_write(self, hook_input: dict, config: Config, phase: str) -> None:
        """Dispatch a Write tool event to the file-write recorder.

        Example:
            >>> Recorder(state)._dispatch_write({}, config, "write-code")  # doctest: +SKIP
        """
        self._record_file_write(hook_input.get("tool_input", {}), config, phase)

    TOOL_RECORDERS: dict = {
        "Skill": _dispatch_skill,
        "Write": _dispatch_write,
        "Edit": _dispatch_edit,
        "Bash": _dispatch_bash,
    }

    def record(self, hook_input: dict, config: Config) -> None:
        """Record state changes for a completed tool use.

        Looks up the dispatch handler for ``hook_input["tool_name"]``;
        unknown tools are silently ignored so the recorder never blocks
        the session on a tool it doesn't model.

        Args:
            hook_input (dict): PostToolUse payload from the hook stdin.
            config (Config): Runtime configuration.

        Raises:
            ValueError: Propagated from inner recorders that explicitly
                raise on parse failures (e.g. malformed PR-create JSON).

        Example:
            >>> Recorder(state).record({"tool_name": "Write"}, config)  # doctest: +SKIP
        """
        handler = self.TOOL_RECORDERS.get(hook_input.get("tool_name", ""))
        if handler is None:
            return
        handler(self, hook_input, config, self.state.current_phase)

    def _record_skill(self, tool_input: dict, phase: str) -> None:
        """Record a Skill invocation as a phase transition.

        Detects the parallel ``explore``↔``research`` case so research
        can launch without prematurely closing an in-flight explore.

        Args:
            tool_input (dict): Raw ``tool_input`` from the hook payload.
            phase (str): Currently active phase (unused — passed for
                dispatch-signature uniformity).

        Example:
            >>> Recorder(state)._record_skill({"command": "/plan"}, "")  # doctest: +SKIP
        """
        skill = extract_skill_name({"tool_input": tool_input})
        current = self.state.current_phase
        parallel = is_parallel_explore_research(
            current, self.state.get_phase_status(current) if current else None, skill
        )
        self.record_phase_transition(current, skill, parallel=parallel)

    def _record_file_write(self, tool_input: dict, config: Config, phase: str) -> None:
        """Record a Write tool event, with specs-phase path canonicalization.

        Specs writes (vision/decision) get their path normalized to the
        config-relative form before recording so all docs entries in
        state.jsonl share one path format. Mismatched paths are dropped
        rather than recorded under the wrong key.

        Args:
            tool_input (dict): Raw ``tool_input`` from the hook payload.
            config (Config): Runtime configuration.
            phase (str): Currently active phase.

        Example:
            >>> Recorder(state)._record_file_write({"file_path": "x"}, config, "write-code")  # doctest: +SKIP
        """
        file_path = tool_input.get("file_path", "")
        is_plan = bool(file_path and file_path.endswith(config.plan_file_path))
        if self._is_specs_phase_mismatch(phase, file_path, config):
            return
        record_path = self._canonicalize_specs_path(phase, file_path, config)
        self.record_write(phase, record_path, is_plan)
        if is_plan:
            self.record_plan_metadata(file_path)
            self.record_plan_sections(file_path)

    @staticmethod
    def _canonicalize_specs_path(phase: str, file_path: str, config: Config) -> str:
        """Store vision/decision docs under their config-relative path so all
        specs doc entries in state.jsonl use the same format (matches architecture/backlog).

        Args:
            phase (str): Currently active phase.
            file_path (str): Raw path from the Write event.
            config (Config): Runtime configuration.

        Returns:
            str: Canonical config-relative path for vision/decision; the
            original ``file_path`` for any other phase.

        Example:
            >>> Recorder._canonicalize_specs_path("vision", "/abs/v.md", config)  # doctest: +SKIP
        """
        canonical = {
            "vision": config.product_vision_file_path,
            "decision": config.decisions_file_path,
        }.get(phase)
        return canonical if canonical else file_path

    @staticmethod
    def _is_specs_phase_mismatch(phase: str, file_path: str, config: Config) -> bool:
        """True when the write path doesn't match the specs phase's canonical doc path.

        Args:
            phase (str): Currently active phase.
            file_path (str): Raw path from the Write event.
            config (Config): Runtime configuration.

        Returns:
            bool: True if the phase expects a specific doc path and
            ``file_path`` doesn't end with it.

        Example:
            >>> Recorder._is_specs_phase_mismatch("vision", "/abs/x.md", config)  # doctest: +SKIP
        """
        expected = {
            "vision": config.product_vision_file_path,
            "decision": config.decisions_file_path,
        }.get(phase)
        if not expected:
            return False
        return not (file_path and file_path.endswith(expected))

    def _record_bash(self, tool_input: dict, tool_output: str, phase: str) -> None:
        """Record a Bash tool event — fans out to test/deps/PR/CI recorders.

        Args:
            tool_input (dict): Raw ``tool_input`` (must include ``"command"``).
            tool_output (str): Raw stdout from the command.
            phase (str): Currently active phase.

        Example:
            >>> Recorder(state)._record_bash({"command": "pytest"}, "", "write-tests")  # doctest: +SKIP
        """
        command = tool_input.get("command", "")

        self.record_test_execution(phase, command)

        if phase == "pr-create" and command.startswith("gh pr create"):
            self.record_pr_create(tool_output)
        if phase == "ci-check" and command.startswith("gh pr checks"):
            self.record_ci_check(tool_output)
