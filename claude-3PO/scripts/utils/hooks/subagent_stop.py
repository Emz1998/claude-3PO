"""utils.hooks.subagent_stop — orchestration helpers for the SubagentStop hook.

Extracted from ``dispatchers/subagent_stop.py`` so the dispatcher file holds
only ``main()``. After the 7-phase MVP trim, the only remaining responsibility
is recording agent completion and re-resolving — there are no review phases
to validate against.
"""

from lib.hook import Hook
from lib.state_store import StateStore
from utils.resolver import resolve
from config import Config


def record_agent_completion(state: StateStore, config: Config, agent_id: str) -> None:
    """Mark the agent done and resolve.

    No-op when ``agent_id`` is missing — without an id we can't match the
    in-progress row to update. Resolver ``ValueError`` is converted to
    ``Hook.discontinue`` so terminal-state errors stop the workflow cleanly
    rather than leaking the exception.

    Args:
        state (StateStore): Live workflow state.
        config (Config): Workflow configuration, forwarded to ``resolve``.
        agent_id (str): Tool-use id from the SubagentStop payload.

    Example:
        >>> record_agent_completion(state, config, "toolu_01abc")  # doctest: +SKIP

    SideEffect:
        Flips the agent row's status to ``completed`` and runs the resolver,
        which may advance the current phase.
    """
    # Empty agent_id means the payload can't identify which in-progress row to
    # update — silently bail rather than corrupt an unrelated row.
    if not agent_id:
        return
    state.update_agent_status(agent_id, "completed")
    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))
