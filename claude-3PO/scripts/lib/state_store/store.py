"""store.py — :class:`StateStore` facade over the workflow slices.

:class:`StateStore` is the single public entry-point callers import. It
inherits :class:`BaseState` so every shared accessor (``load``, ``phases``,
``add_agent`` …) remains reachable as ``state.<method>`` with zero churn.
Three named sub-attributes — ``state.build``, ``state.implement``,
``state.specs`` — expose the workflow-specific slices with explicit
ownership at every call site (no ``__getattr__`` magic).
"""

from pathlib import Path
from typing import Any

from .base import BaseState
from .build import BuildState
from .implement import ImplementState
from .specs import SpecsState


class StateStore(BaseState):
    """
    Session-scoped state facade composing the three workflow slices.

    ``self`` carries every shared :class:`BaseState` method directly, while
    ``self.build``, ``self.implement`` and ``self.specs`` hold the workflow
    slices. All four objects share the same file + lock because every slice
    was constructed against ``self``.

    Example:
        >>> state = StateStore(Path("/tmp/state.jsonl"), "abc")  # doctest: +SKIP
        Return: <StateStore>
    """

    def __init__(
        self,
        state_path: Path,
        session_id: str,
        default_state: dict[str, Any] | None = None,
    ) -> None:
        """
        Bind the store to a path/session and attach the workflow slices.

        Args:
            state_path (Path): JSONL file backing the store.
            session_id (str): Unique session identifier.
            default_state (dict[str, Any] | None): Initial dict for a
                previously-unseen session. Defaults to ``{}``.

        Returns:
            None: Constructor — wires up the sub-slices.

        SideEffect:
            Sets ``self.build``, ``self.implement``, ``self.specs`` to
            workflow slices bound to ``self``.

        Example:
            >>> StateStore(Path("/tmp/state.jsonl"), "abc")  # doctest: +SKIP
            Return: <StateStore>
            SideEffect:
                self.build = <BuildState>
                self.implement = <ImplementState>
                self.specs = <SpecsState>
        """
        # Base initializer sets the path, session, lock — everything I/O-bound.
        super().__init__(state_path, session_id, default_state)
        # Named sub-attributes; ownership is visible at call sites.
        self.build = BuildState(self)
        self.implement = ImplementState(self)
        self.specs = SpecsState(self)
