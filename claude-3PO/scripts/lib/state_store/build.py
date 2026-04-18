"""build.py — Build-workflow slice of :class:`StateStore`.

Holds accessors that only exist for the *build* workflow (created-tasks
ledger + clarify-phase bookkeeping). The class is a thin wrapper around a
shared :class:`BaseState` — it never owns its own file handle or lock, so
every read/write still routes through the one atomic
:meth:`BaseState.update` cycle that the rest of the system already trusts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseState


class BuildState:
    """
    Build-workflow accessors exposed via ``state.build`` on :class:`StateStore`.

    All methods delegate to the shared :class:`BaseState` so a single JSONL
    line and a single filelock back every workflow slice.

    Example:
        >>> state.build.created_tasks  # doctest: +SKIP
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
            >>> BuildState(base)  # doctest: +SKIP
            Return: <BuildState>
        """
        # Composition, not inheritance — make the owning base explicit.
        self._base = base

    # ── Created tasks (build workflow — tracks TaskCreate completions) ─

    @property
    def created_tasks(self) -> list[str]:
        """
        Task subjects already created via TaskCreate during build.

        Returns:
            list[str]: Subjects recorded after a successful TaskCreate.

        Example:
            >>> store.build.created_tasks  # doctest: +SKIP
            Return: ['Write tests']
        """
        return self._base.load().get("created_tasks", [])

    def add_created_task(self, subject: str) -> None:
        """
        Record *subject* as a created task (deduplicated).

        Args:
            subject (str): Subject of the just-created task.

        Returns:
            None: Side-effects only — duplicates silently ignored.

        SideEffect:
            Appends to state[created_tasks].

        Example:
            >>> store.build.add_created_task("Write tests")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[created_tasks] = [..., "Write tests"]
        """
        def _add(d: dict) -> None:
            ct = d.get("created_tasks", [])
            # Dedup — TaskCreate hooks may fire twice on retry.
            if subject not in ct:
                ct.append(subject)
            d["created_tasks"] = ct

        self._base.update(_add)

    # ── Clarify phase fields (build workflow) ─────────────────────

    def get_clarify_phase(self) -> dict | None:
        """
        Look up the clarify phase dict from ``state.phases``.

        Returns:
            dict | None: The phase entry whose ``name`` is ``"clarify"``,
            or ``None`` when no clarify phase was added.

        Example:
            >>> store.build.get_clarify_phase()  # doctest: +SKIP
            Return: {'name': 'clarify', 'status': 'in_progress'}
        """
        # Linear scan — phase lists are short.
        for p in self._base.phases:
            if p.get("name") == "clarify":
                return p
        return None

    def set_clarify_session(self, headless_session_id: str) -> None:
        """
        Stamp the headless session id and zero the iteration counter.

        Args:
            headless_session_id (str): Session id returned by the initial
                headless ``claude -p`` clarity check.

        Returns:
            None: Side-effects only — no-op when clarify phase is missing.

        SideEffect:
            Sets state[phases][clarify][headless_session_id]; resets iteration_count.

        Example:
            >>> store.build.set_clarify_session("sess_abc123")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[phases][clarify][headless_session_id] = "sess_abc123"
        """
        def _set(d: dict) -> None:
            # Find the clarify phase entry; first match wins.
            for p in d.get("phases", []):
                if p.get("name") == "clarify":
                    p["headless_session_id"] = headless_session_id
                    # Reset iteration_count — caller is starting a fresh loop.
                    p["iteration_count"] = 0
                    break

        self._base.update(_set)

    def bump_clarify_iteration(self) -> None:
        """
        Increment ``iteration_count`` on the clarify phase by one.

        No-op if the clarify phase is missing — the caller is expected to
        verify it exists before incrementing.

        Returns:
            None: Side-effects only.

        SideEffect:
            Increments state[phases][clarify][iteration_count].

        Example:
            >>> store.build.bump_clarify_iteration()  # doctest: +SKIP
            Return: None
            SideEffect:
                state[phases][clarify][iteration_count] = (previous + 1)
        """
        def _bump(d: dict) -> None:
            # First clarify phase entry — unique per session by convention.
            for p in d.get("phases", []):
                if p.get("name") == "clarify":
                    p["iteration_count"] = int(p.get("iteration_count", 0)) + 1
                    break

        self._base.update(_bump)
