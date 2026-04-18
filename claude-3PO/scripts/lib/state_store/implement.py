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
