"""store.py — :class:`StateStore` facade over the implement workflow slice.

:class:`StateStore` is the single public entry-point callers import. It
inherits :class:`BaseState` so every shared accessor (``load``, ``phases``,
``add_agent`` …) remains reachable as ``state.<method>`` with zero churn.
A single named sub-attribute — ``state.implement`` — exposes the
implement-specific slice with explicit ownership at every call site
(no ``__getattr__`` magic).
"""

from pathlib import Path
from typing import Any

from .base import BaseState
from .implement import ImplementState


class StateStore(BaseState):
    """
    Single-session state facade composing the implement workflow slice.

    ``self`` carries every shared :class:`BaseState` method directly, while
    ``self.implement`` holds the implement-workflow slice. Both objects share
    the same file + lock because the slice was constructed against ``self``.

    Example:
        >>> state = StateStore(Path("/tmp/state.json"))  # doctest: +SKIP
        Return: <StateStore>
    """

    def __init__(
        self,
        state_path: Path,
        default_state: dict[str, Any] | None = None,
    ) -> None:
        """
        Bind the store to ``state.json`` and attach the implement slice.

        Args:
            state_path (Path): JSON file backing the store.
            default_state (dict[str, Any] | None): Initial dict used when
                ``state.json`` is missing or empty. Defaults to ``{}``.

        Returns:
            None: Constructor — wires up the sub-slice.

        SideEffect:
            Sets ``self.implement`` to an ImplementState slice bound to ``self``.

        Example:
            >>> StateStore(Path("/tmp/state.json"))  # doctest: +SKIP
            Return: <StateStore>
            SideEffect:
                self.implement = <ImplementState>
        """
        # Base initializer sets the path, lock — everything I/O-bound.
        super().__init__(state_path, default_state)
        # Named sub-attribute; ownership is visible at call sites.
        self.implement = ImplementState(self)
