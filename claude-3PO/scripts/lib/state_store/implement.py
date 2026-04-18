"""implement.py — Implement-workflow slice of :class:`StateStore`.

Holds accessors that only exist for the *implement* workflow (project task
tree, plan-files-to-modify, the Recorder-facing ``add_project_task`` sink).
The class is a thin wrapper around a shared :class:`BaseState` — every
mutation routes through :meth:`BaseState.update` so the atomic
read-modify-write cycle is preserved regardless of which slice was the
caller.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from models.state import Task

if TYPE_CHECKING:
    from .base import BaseState


class ImplementState:
    """
    Implement-workflow accessors exposed via ``state.implement``.

    All methods delegate to the shared :class:`BaseState` so a single JSONL
    line and a single filelock back every workflow slice.

    Example:
        >>> state.implement.project_tasks  # doctest: +SKIP
        Return: []
    """

    def __init__(self, base: "BaseState") -> None:
        """
        Bind this slice to the shared :class:`BaseState`.

        Args:
            base (BaseState): The StateStore-owned base that performs I/O.

        Returns:
            None: Stores *base* on ``self``.

        Example:
            >>> ImplementState(base)  # doctest: +SKIP
            Return: <ImplementState>
        """
        # Composition, not inheritance — make the owning base explicit.
        self._base = base

    # ── Project tasks (implement workflow) ─────────────────────────

    @property
    def project_tasks(self) -> list[dict]:
        """
        Top-level project tasks for the implement workflow.

        Returns:
            list[dict]: Task records, each optionally carrying a ``subtasks`` list.

        Example:
            >>> store.implement.project_tasks  # doctest: +SKIP
            Return: [{'id': 'T1', 'subtasks': []}]
        """
        return self._base.load().get("project_tasks", [])

    def set_project_tasks(self, tasks: list[dict]) -> None:
        """
        Replace the project-task list wholesale.

        Args:
            tasks (list[dict]): New project-task records.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[project_tasks].

        Example:
            >>> store.implement.set_project_tasks([{"id": "T1"}])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks] = [{"id": "T1"}]
        """
        self._base.set("project_tasks", tasks)

    def add_subtask(self, parent_task_id: str, subtask: dict | str) -> None:
        """
        Append a subtask under the project task whose ``id`` matches.

        Dedup logic depends on type: dict subtasks dedupe on ``task_id``,
        string subtasks on the literal value. Mixed types in one parent are
        legal but discouraged.

        Args:
            parent_task_id (str): ID of the project task to attach to.
            subtask (dict | str): Subtask record or label.

        Returns:
            None: Side-effects only — no-op when parent is missing.

        SideEffect:
            Appends to state[project_tasks][i][subtasks].

        Example:
            >>> store.implement.add_subtask("T1", {"task_id": "T1.1"})  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks][i][subtasks].append(subtask)
        """
        def _add(d: dict) -> None:
            ptasks = d.get("project_tasks", [])
            # Find the parent; skip if no match.
            for pt in ptasks:
                if pt.get("id") == parent_task_id:
                    subs = pt.setdefault("subtasks", [])
                    # Dedup key differs by shape: dicts use task_id, strings use value.
                    if isinstance(subtask, dict):
                        if not any(
                            s.get("task_id") == subtask.get("task_id")
                            for s in subs
                            if isinstance(s, dict)
                        ):
                            subs.append(subtask)
                    else:
                        if subtask not in subs:
                            subs.append(subtask)
                    break

        self._base.update(_add)

    def set_subtask_completed(self, parent_task_id: str, task_id: str) -> None:
        """
        Mark a specific subtask under a parent task as completed.

        Args:
            parent_task_id (str): Parent project task ID.
            task_id (str): Subtask task_id to mark completed.

        Returns:
            None: Side-effects only — no-op when either id is missing.

        SideEffect:
            Sets state[project_tasks][i][subtasks][j][status].

        Example:
            >>> store.implement.set_subtask_completed("T1", "T1.1")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks][i][subtasks][j][status] = "completed"
        """
        def _complete(d: dict) -> None:
            ptasks = d.get("project_tasks", [])
            # Find the parent task first …
            for pt in ptasks:
                if pt.get("id") == parent_task_id:
                    # … then the matching subtask inside it.
                    for sub in pt.get("subtasks", []):
                        if isinstance(sub, dict) and sub.get("task_id") == task_id:
                            sub["status"] = "completed"
                            break
                    break

        self._base.update(_complete)

    def set_project_task_completed(self, parent_task_id: str) -> None:
        """
        Mark a top-level project task as completed.

        Args:
            parent_task_id (str): Project task ID.

        Returns:
            None: Side-effects only — no-op when parent is missing.

        SideEffect:
            Sets state[project_tasks][i][status].

        Example:
            >>> store.implement.set_project_task_completed("T1")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks][i][status] = "completed"
        """
        def _complete(d: dict) -> None:
            ptasks = d.get("project_tasks", [])
            for pt in ptasks:
                if pt.get("id") == parent_task_id:
                    pt["status"] = "completed"
                    break

        self._base.update(_complete)

    def get_parent_for_subtask(self, task_id: str) -> str | None:
        """
        Find the parent project-task ID that owns *task_id*.

        Args:
            task_id (str): Subtask task_id.

        Returns:
            str | None: Parent project-task ID, or ``None`` when not found.

        Example:
            >>> store.implement.get_parent_for_subtask("T1.1")  # doctest: +SKIP
            Return: 'T1'
        """
        # Two-level scan — project tasks and their subtasks.
        for pt in self.project_tasks:
            for sub in pt.get("subtasks", []):
                if isinstance(sub, dict) and sub.get("task_id") == task_id:
                    return pt.get("id")
        return None

    # ── Plan files to modify (implement workflow) ──────────────────

    @property
    def plan_files_to_modify(self) -> list[str]:
        """
        Files the plan declared the implement workflow should modify.

        Returns:
            list[str]: Planned target files.

        Example:
            >>> store.implement.plan_files_to_modify  # doctest: +SKIP
            Return: ['src/foo.py']
        """
        return self._base.load().get("plan_files_to_modify", [])

    def set_plan_files_to_modify(self, files: list[str]) -> None:
        """
        Replace the plan-files-to-modify list.

        Args:
            files (list[str]): New target file paths.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[plan_files_to_modify].

        Example:
            >>> store.implement.set_plan_files_to_modify(["src/foo.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[plan_files_to_modify] = ["src/foo.py"]
        """
        self._base.set("plan_files_to_modify", files)

    # ── Flat-API sink (Recorder-facing) ────────────────────────────

    def add_project_task(self, task: Task) -> None:
        """
        Append a :class:`Task` to ``project_tasks`` (dedup by ``task_id``).

        Dedup makes the Recorder safe to re-dispatch the same TaskCreate
        without producing duplicate project_tasks entries.

        Args:
            task (Task): Pydantic task record.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[project_tasks] (dedup by task_id).

        Example:
            >>> store.implement.add_project_task(Task(task_id="T-1", subject="x"))  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks] = [..., task.model_dump(])
        """
        def _add(d: dict) -> None:
            tasks = d.setdefault("project_tasks", [])
            # Skip if any existing record already owns this task_id.
            if not any(t.get("task_id") == task.task_id for t in tasks):
                tasks.append(task.model_dump())

        self._base.update(_add)
