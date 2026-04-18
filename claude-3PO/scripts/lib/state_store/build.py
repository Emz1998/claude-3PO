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
