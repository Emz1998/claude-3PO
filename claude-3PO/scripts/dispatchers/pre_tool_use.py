#!/usr/bin/env python3
"""PreToolUse hook — gate every tool call through the matching guardrail.

Serves the Claude Code ``PreToolUse`` event. Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id or no active workflow.
    2. Look up the per-tool guard in ``TOOL_GUARDS`` (keyed by ``tool_name``).
       Tools without a guard are silently allowed.
    3. Run the guard. On ``"block"`` log the violation and call
       ``Hook.advanced_block`` — emits a ``permissionDecision: deny`` JSON
       payload so the Claude Code UI shows a structured denial reason.
    4. On ``"allow"`` for ``Skill`` invocations, apply phase-skill side effects
       (state mutations + auto-advance) via :func:`_apply_phase_skill_effects`.
    5. Always finish with ``Hook.system_message`` so the optional guard message
       reaches the model regardless of decision.

The Skill side-effect pass at step 4 used to live inside ``PhaseGuard``; it was
extracted so the guard stays a pure pass/fail validator and the dispatcher owns
the post-Allow mutations (SRP refactor).
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from guardrails import TOOL_GUARDS
from lib.extractors import extract_skill_name
from lib.hook import Hook
from lib.state_store import StateStore
from lib.violations import log_violation, extract_action
from config import Config
from utils.recorder import Recorder
from utils.resolver import Resolver


PRE_WORKFLOW_PHASE = "pre-workflow"


def resolve_violation_phase(
    state: StateStore, config: Config, tool_name: str, hook_input: dict
) -> str:
    """Pick the phase label written into a violation row.

    Cascading priority:

    1. ``state.current_phase`` — the phase the user was *in* when the block
       fired. Most accurate signal.
    2. For a ``Skill`` tool with no active phase: the attempted skill name.
       Invoking a skill IS what establishes a phase, so its name is the most
       meaningful label even though the phase isn't set yet.
    3. Otherwise: the ``pre-workflow`` sentinel. We deliberately do NOT fall
       back to the first workflow phase — labelling a pre-``/vision`` Write as
       ``vision`` would misleadingly imply the user had entered that phase.

    Args:
        state (StateStore): Live workflow state for the current session.
        config (Config): Workflow configuration (currently unused; kept in the
            signature so future cascades can consult it without re-threading).
        tool_name (str): The tool being attempted, e.g. ``"Skill"`` or ``"Write"``.
        hook_input (dict): Raw PreToolUse hook payload, used only to extract the
            attempted skill name when ``tool_name == "Skill"``.

    Returns:
        str: The phase label to record on the violation.

    Example:
        >>> resolve_violation_phase(state, config, "Skill", hook_input)  # doctest: +SKIP
        'vision'
    """
    if state.current_phase:
        return state.current_phase
    if tool_name == "Skill":
        from lib.extractors import extract_skill_name
        skill = extract_skill_name(hook_input)
        if skill:
            return skill
    return PRE_WORKFLOW_PHASE


def main() -> None:
    """Entry point — runs once per PreToolUse event.

    Early-exit cascade: no session_id → no active workflow → no guard registered
    for this tool → run the guard and either ``advanced_block`` (deny) or
    ``system_message`` (allow, optionally with a status nudge).

    Example:
        >>> main()  # doctest: +SKIP — reads JSON from stdin and exits
    """
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(SCRIPTS_DIR / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    guard = TOOL_GUARDS.get(tool_name)
    if not guard:
        sys.exit(0)

    config = Config()
    decision, message = guard(hook_input, config, state)

    if decision == "block":
        log_violation(
            session_id=session_id,
            workflow_type=state.get("workflow_type", "build"),
            story_id=state.get("story_id"),
            prompt_summary=state.get("prompt_summary"),
            phase=resolve_violation_phase(state, config, tool_name, hook_input),
            tool=tool_name,
            action=extract_action(tool_name, hook_input),
            reason=message,
        )
        Hook.advanced_block("PreToolUse", message)
    else:
        if tool_name == "Skill":
            _apply_phase_skill_effects(hook_input, config, state)
        Hook.system_message(message)


def _apply_phase_skill_effects(hook_input: dict, config: Config, state: StateStore) -> None:
    """Apply state mutations + auto-advance for the meta-skills.

    Runs only after PhaseGuard returns Allow for one of the three meta-skills
    that mutate workflow state rather than enter a phase:

    - ``/continue`` — record the user's intent to keep going on the current
      phase, then auto-start the next phase (respecting checkpoints).
    - ``/plan-approved`` — same record + auto-start, but ``skip_checkpoint=True``
      because plan approval IS the checkpoint.
    - ``/revise-plan`` — record only; the user will re-enter the plan phase
      manually so no auto-advance fires.

    This logic used to live inside ``PhaseGuard``; extracting it here keeps the
    guard a pure validator and concentrates the post-Allow side effects in the
    dispatcher (recent SRP refactor).

    Args:
        hook_input (dict): Raw PreToolUse hook payload (used to read the skill name).
        config (Config): Workflow configuration passed through to ``Resolver``.
        state (StateStore): Live workflow state; mutated by ``Recorder`` and
            possibly advanced by ``Resolver``.

    Example:
        >>> _apply_phase_skill_effects(hook_input, config, state)  # doctest: +SKIP
    """
    skill = extract_skill_name(hook_input)
    if skill not in ("continue", "plan-approved", "revise-plan"):
        return
    current = state.current_phase
    status = state.get_phase_status(current) if current else ""
    Recorder(state).apply_phase_skill(skill, current or "", status or "")
    if skill == "plan-approved":
        Resolver(config, state).auto_start_next(skip_checkpoint=True)
    elif skill == "continue":
        Resolver(config, state).auto_start_next()


if __name__ == "__main__":
    main()
