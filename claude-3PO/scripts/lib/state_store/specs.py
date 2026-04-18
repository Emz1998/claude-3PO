"""specs.py — Specs-workflow slice of :class:`StateStore`.

Holds accessors that only exist for the *specs* workflow (per-doc-key
written flag and path bookkeeping). The class is a thin wrapper around a
shared :class:`BaseState` — every read/write still routes through the
one atomic :meth:`BaseState.update` cycle the rest of the system trusts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseState


class SpecsState:
    """
    Specs-workflow accessors exposed via ``state.specs`` on :class:`StateStore`.

    All methods delegate to the shared :class:`BaseState` so a single JSONL
    line and a single filelock back every workflow slice.

    Example:
        >>> state.specs.docs  # doctest: +SKIP
        Return: {}
    """

    def __init__(self, base: "BaseState") -> None:
        """
        Bind this slice to the shared :class:`BaseState`.

        Args:
            base (BaseState): The StateStore-owned base that performs I/O.

        Returns:
            None: Stores *base* on ``self``.

        Example:
            >>> SpecsState(base)  # doctest: +SKIP
            Return: <SpecsState>
        """
        # Composition, not inheritance — make the owning base explicit.
        self._base = base
