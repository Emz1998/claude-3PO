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
    Single-session state facade composing the three workflow slices.

    ``self`` carries every shared :class:`BaseState` method directly, while
    ``self.build``, ``self.implement`` and ``self.specs`` hold the workflow
    slices. All four objects share the same file + lock because every slice
    was constructed against ``self``.

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
        Bind the store to ``state.json`` and attach the workflow slices.

        Args:
            state_path (Path): JSON file backing the store.
            default_state (dict[str, Any] | None): Initial dict used when
                ``state.json`` is missing or empty. Defaults to ``{}``.

        Returns:
            None: Constructor — wires up the sub-slices.

        SideEffect:
            Sets ``self.build``, ``self.implement``, ``self.specs`` to
            workflow slices bound to ``self``.

        Example:
            >>> StateStore(Path("/tmp/state.json"))  # doctest: +SKIP
            Return: <StateStore>
            SideEffect:
                self.build = <BuildState>
                self.implement = <ImplementState>
                self.specs = <SpecsState>
        """
        # Base initializer sets the path, lock — everything I/O-bound.
        super().__init__(state_path, default_state)
        # Named sub-attributes; ownership is visible at call sites.
        self.build = BuildState(self)
        self.implement = ImplementState(self)
        self.specs = SpecsState(self)
