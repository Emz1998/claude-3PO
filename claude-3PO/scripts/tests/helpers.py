"""Test helpers, including dispatcher orchestration wrappers.

The orchestration wrappers mirror the production dispatchers (pre_tool_use,
subagent_stop) so tests assert the full guard-then-side-effects flow that
users actually experience — not just the pure-validator step.
"""


def make_hook_input(tool_name: str = "", tool_input: dict | None = None, **extra) -> dict:
    d = {"tool_name": tool_name, "tool_input": tool_input or {}}
    d.update(extra)
    return d


def invoke_phase_guard(hook: dict, config, state):
    """Run PhaseGuard like dispatchers/pre_tool_use does for a Skill.

    On Allow for /continue, /plan-approved, /revise-plan: apply state mutations
    via Recorder + auto-advance via Resolver.
    """
    from guardrails import phase_guard
    from lib.extractors import extract_skill_name
    from utils.recorder import Recorder
    from utils.resolver import Resolver

    decision, message = phase_guard(hook, config, state)
    if decision != "allow":
        return decision, message

    skill = extract_skill_name(hook)
    if skill in ("continue", "plan-approved", "revise-plan"):
        current = state.current_phase
        status = state.get_phase_status(current) if current else ""
        Recorder(state).apply_phase_skill(skill, current or "", status or "")
        if skill == "plan-approved":
            Resolver(config, state).auto_start_next(skip_checkpoint=True)
        elif skill == "continue":
            Resolver(config, state).auto_start_next()
    return decision, message


def invoke_agent_report_guard(hook: dict, config, state):
    """Run AgentReportGuard like dispatchers/subagent_stop does on Allow."""
    from guardrails.agent_report_guard import AgentReportGuard
    from utils.recorder import Recorder
    from utils.resolver import resolve

    guard = AgentReportGuard(hook, config, state)
    decision, message = guard.validate()
    if decision != "allow":
        return decision, message

    recorder = Recorder(state)
    if guard.phase in AgentReportGuard.SPECS_PHASES:
        recorder.write_specs_doc(guard.phase, guard.content, config)
    else:
        recorder.record_scores(guard.phase, guard.content)
        recorder.record_verdict(guard.phase, guard.content)
        recorder.record_revision_files(
            guard.phase, guard.review_files, guard.review_tests
        )
    resolve(config, state)
    return decision, message
