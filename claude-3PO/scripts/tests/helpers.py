"""Test helpers, including dispatcher orchestration wrappers.

The orchestration wrappers mirror the production dispatchers (pre_tool_use,
subagent_stop) so tests assert the full guard-then-side-effects flow that
users actually experience — not just the pure-validator step. Post-Allow
state mutations are inlined here (not delegated to Recorder) because the
new Recorder API no longer exposes phase-skill / agent-report helpers.
"""

from lib.extractors import (
    extract_skill_name,
    extract_scores,
    extract_verdict,
)
from lib.scoring import scores_valid, verdict_valid


def make_hook_input(tool_name: str = "", tool_input: dict | None = None, **extra) -> dict:
    d = {"tool_name": tool_name, "tool_input": tool_input or {}}
    d.update(extra)
    return d


def _apply_phase_skill(state, skill: str, current: str, status: str) -> None:
    """Inline replacement for the old Recorder.apply_phase_skill side-effects."""
    if skill == "continue" and status == "in_progress":
        state.set_phase_completed(current)
    elif skill == "plan-approved" and status == "in_progress":
        state.set_phase_completed("plan-review")
    elif skill == "revise-plan":
        def _reopen(d: dict) -> None:
            for p in d.get("phases", []):
                if p["name"] == "plan-review":
                    p["status"] = "in_progress"
                    break
            plan = d.setdefault("plan", {})
            plan["revised"] = False
            plan["reviews"] = []

        state.update(_reopen)


def invoke_phase_guard(hook: dict, config, state):
    """Run PhaseGuard like dispatchers/pre_tool_use does for a Skill.

    On Allow for /continue, /plan-approved, /revise-plan: apply state mutations
    inline (no longer through Recorder) + auto-advance via Resolver.
    """
    from handlers.guardrails import phase_guard
    from utils.resolver import Resolver

    decision, message = phase_guard(hook, config, state)
    if decision != "allow":
        return decision, message

    skill = extract_skill_name(hook)
    if skill in ("continue", "plan-approved", "revise-plan"):
        current = state.current_phase
        status = state.get_phase_status(current) if current else ""
        _apply_phase_skill(state, skill, current or "", status or "")
        if skill == "plan-approved":
            Resolver(config, state).auto_start_next(skip_checkpoint=True)
        elif skill == "continue":
            Resolver(config, state).auto_start_next()
    return decision, message


def _apply_review_allow(state, phase: str, content: str,
                        review_files: list[str], review_tests: list[str]) -> None:
    """Inline replacement for the old Recorder review-side-effects."""
    if phase in ("plan-review", "code-review"):
        _, scores = scores_valid(content, extract_scores)
        if phase == "plan-review":
            state.add_plan_review(scores)
        else:
            state.add_code_review(scores)

    if phase == "test-review":
        _, verdict = verdict_valid(content, extract_verdict)
        state.add_test_review(verdict)
    if phase in ("quality-check", "validate"):
        _, verdict = verdict_valid(content, extract_verdict)
        state.set_quality_check_result(verdict)

    if phase == "code-review" and review_files:
        state.set_files_to_revise(review_files)
        state.set_code_tests_to_revise(review_tests)
    elif phase == "test-review" and review_files:
        state.set_test_files_to_revise(review_files)


def _apply_specs_allow(state, phase: str, content: str, config) -> None:
    """Inline replacement for the old Recorder.write_specs_doc side-effects."""
    from utils.specs_writer import write_doc, write_backlog

    if phase == "architect":
        path = config.architecture_file_path
        write_doc(content, path)
        state.specs.set_doc_written("architecture", True)
        state.specs.set_doc_path("architecture", path)
    elif phase == "backlog":
        md_path = config.backlog_md_file_path
        json_path = config.backlog_json_file_path
        write_backlog(content, md_path, json_path)
        state.specs.set_doc_written("backlog", True)
        state.specs.set_doc_md_path("backlog", md_path)
        state.specs.set_doc_json_path("backlog", json_path)


def invoke_agent_report_guard(hook: dict, config, state):
    """Run AgentReportGuard like dispatchers/subagent_stop does on Allow."""
    from handlers.guardrails.agent_report_guard import AgentReportGuard
    from utils.resolver import resolve

    guard = AgentReportGuard(hook, config, state)
    decision, message = guard.validate()
    if decision != "allow":
        return decision, message

    if guard.phase in AgentReportGuard.SPECS_PHASES:
        _apply_specs_allow(state, guard.phase, guard.content, config)
    else:
        _apply_review_allow(
            state, guard.phase, guard.content,
            guard.review_files, guard.review_tests,
        )
    resolve(config, state)
    return decision, message
