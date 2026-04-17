"""Predicate for the parallel explore+research transition.

Used by both PhaseGuard (allow research while explore is in_progress)
and Recorder (track parallel transition without completing explore).
"""


def is_parallel_explore_research(
    current_phase: str | None, current_status: str | None, next_skill: str
) -> bool:
    """True when entering 'research' while 'explore' is still in_progress."""
    return (
        current_phase == "explore"
        and current_status == "in_progress"
        and next_skill == "research"
    )
