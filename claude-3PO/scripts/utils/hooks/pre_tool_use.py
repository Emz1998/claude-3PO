"""utils.hooks.pre_tool_use — orchestration helpers for the PreToolUse hook.

Extracted from ``dispatchers/pre_tool_use.py`` so the dispatcher file holds
only ``main()``. The only helper here is the phase-label resolver used when
writing a violation row.
"""

from lib.extractors import extract_skill_name
from lib.state_store import StateStore
from config import Config


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
    # Cascade: active phase > attempted skill name > pre-workflow sentinel.
    if state.current_phase:
        return state.current_phase
    if tool_name == "Skill":
        skill = extract_skill_name(hook_input)
        if skill:
            return skill
    return PRE_WORKFLOW_PHASE
