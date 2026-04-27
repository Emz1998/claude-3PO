"""utils.hooks.task_created — orchestration helpers for the TaskCreated hook.

Extracted from ``dispatchers/task_created.py`` so the dispatcher file holds
only ``main()``. The single helper here applies the side-effects an allowed
``TaskCreatedGuard`` has staged on its instance attributes.
"""

from handlers.guardrails.task_created_guard import TaskCreatedGuard
from lib.state_store import StateStore
from utils.recorder import Recorder


def apply_task_effects(guard: TaskCreatedGuard, state: StateStore) -> None:
    """Record the matched implement-workflow subtask exposed by an allowed guard.

    Args:
        guard (TaskCreatedGuard): Already-validated guard exposing the matched
            implement metadata.
        state (StateStore): Live workflow state, mutated by Recorder.

    Example:
        >>> apply_task_effects(guard, state)  # doctest: +SKIP

    SideEffect:
        Appends the matched subtask to ``project_tasks`` via
        ``Recorder.record_task``.
    """
    if guard.matched_implement_parent_id and guard.matched_implement_payload:
        payload = guard.matched_implement_payload
        Recorder(state).record_task(
            task_id=payload.get("task_id", ""),
            subject=payload.get("subject", ""),
            description=payload.get("description", ""),
            parent_task_id=guard.matched_implement_parent_id,
        )
