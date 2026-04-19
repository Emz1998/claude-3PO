"""utils.hooks.task_created — orchestration helpers for the TaskCreated hook.

Extracted from ``dispatchers/task_created.py`` so the dispatcher file holds
only ``main()``. The single helper here applies the side-effects an allowed
``TaskCreatedGuard`` has staged on its instance attributes.
"""

from handlers.guardrails.task_created_guard import TaskCreatedGuard
from lib.state_store import StateStore
from utils.recorder import Recorder


def apply_task_effects(guard: TaskCreatedGuard, state: StateStore) -> None:
    """Record the matched task data exposed by an allowed ``TaskCreatedGuard``.

    Two independent effects, both gated on what the guard actually matched:

    - ``matched_build_subject`` — the new task corresponds to a planned build
      task; record it as the active created task for the build flow (still
      via :meth:`BuildState.add_created_task` since the flat Recorder API
      tracks only project tasks, not build subjects).
    - ``matched_implement_parent_id`` + ``matched_implement_payload`` — the new
      task is a subtask of an implement-workflow parent; append it to the
      flat ``project_tasks`` list with its ``parent_task_id`` set.

    Args:
        guard (TaskCreatedGuard): Already-validated guard exposing the matched
            build/implement metadata.
        state (StateStore): Live workflow state, mutated by Recorder.

    Example:
        >>> apply_task_effects(guard, state)  # doctest: +SKIP

    SideEffect:
        May append a build task via ``BuildState.add_created_task`` and/or
        record an implement subtask via ``Recorder.record_task``.
    """
    # Build + implement effects are independent: the guard may set either,
    # both, or neither depending on which workflow/phase the task belongs to.
    if guard.matched_build_subject:
        state.build.add_created_task(guard.matched_build_subject)
    if guard.matched_implement_parent_id and guard.matched_implement_payload:
        payload = guard.matched_implement_payload
        Recorder(state).record_task(
            task_id=payload.get("task_id", ""),
            subject=payload.get("subject", ""),
            description=payload.get("description", ""),
            parent_task_id=guard.matched_implement_parent_id,
        )
