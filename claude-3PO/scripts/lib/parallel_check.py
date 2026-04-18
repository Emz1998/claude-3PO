"""parallel_check.py — Predicate for the parallel ``explore`` + ``research`` phase transition.

``explore`` and ``research`` are normally sequential phases, but the workflow
allows ``research`` to start while ``explore`` is still in progress as a
deliberate exception. PhaseGuard uses this predicate to permit the overlap;
Recorder uses it to log the transition without prematurely marking ``explore``
as completed. Centralizing the rule keeps both call sites in sync.
"""


def is_parallel_explore_research(
    current_phase: str | None, current_status: str | None, next_skill: str
) -> bool:
    """
    Detect the explore-still-running, research-starting transition.

    Args:
        current_phase (str | None): Name of the active phase, or ``None`` if none.
        current_status (str | None): Status of the active phase
            (``"in_progress"`` is the only one that matters here).
        next_skill (str): Skill being requested by the agent.

    Returns:
        bool: ``True`` only when ``research`` is about to start while
        ``explore`` is still ``in_progress``; ``False`` otherwise.

    Example:
        >>> is_parallel_explore_research("explore", "in_progress", "research")
        True
        >>> is_parallel_explore_research("explore", "completed", "research")
        False
    """
    return (
        current_phase == "explore"
        and current_status == "in_progress"
        and next_skill == "research"
    )
