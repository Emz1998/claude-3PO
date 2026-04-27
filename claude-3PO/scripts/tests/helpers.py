"""Test helpers, including dispatcher orchestration wrappers.

The orchestration wrappers mirror the production dispatchers (pre_tool_use)
so tests assert the full guard-then-side-effects flow that users actually
experience — not just the pure-validator step.
"""

from lib.extractors import extract_skill_name


def make_hook_input(tool_name: str = "", tool_input: dict | None = None, **extra) -> dict:
    d = {"tool_name": tool_name, "tool_input": tool_input or {}}
    d.update(extra)
    return d


def _apply_phase_skill(state, skill: str, current: str, status: str) -> None:
    """Inline replacement for the old Recorder.apply_phase_skill side-effects."""
    if skill == "continue" and status == "in_progress":
        state.set_phase_completed(current)


def invoke_phase_guard(hook: dict, config, state):
    """Run PhaseGuard like dispatchers/pre_tool_use does for a Skill.

    On Allow for /continue: apply state mutations inline + auto-advance via Resolver.
    """
    from handlers.guardrails import phase_guard
    from utils.resolver import Resolver

    decision, message = phase_guard(hook, config, state)
    if decision != "allow":
        return decision, message

    skill = extract_skill_name(hook)
    if skill == "continue":
        current = state.current_phase
        status = state.get_phase_status(current) if current else ""
        _apply_phase_skill(state, skill, current or "", status or "")
        Resolver(config, state).auto_start_next(skip_checkpoint=True)
    return decision, message
