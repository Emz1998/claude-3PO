"""specs.py — Specs-workflow slice of :class:`StateStore`.

Holds accessors that only exist for the *specs* workflow (per-doc-key
written flag and path bookkeeping). The class is a thin wrapper around a
shared :class:`BaseState` — every read/write still routes through the
one atomic :meth:`BaseState.update` cycle the rest of the system trusts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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

    # ── Docs (specs workflow) ─────────────────────────────────────

    @property
    def docs(self) -> dict[str, Any]:
        """
        The docs sub-dict — tracks per-doc-key state for the specs workflow.

        Returns:
            dict[str, Any]: Doc state keyed by doc identifier.

        Example:
            >>> store.specs.docs  # doctest: +SKIP
            Return: {'architecture': {'written': True}}
        """
        return self._base.load().get("docs", {})

    def set_doc_written(self, doc_key: str, written: bool) -> None:
        """
        Toggle the ``written`` flag for *doc_key*.

        Args:
            doc_key (str): Identifier of the doc entry.
            written (bool): ``True`` once the doc is persisted.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[docs][doc_key][written].

        Example:
            >>> store.specs.set_doc_written("architecture", True)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[docs]["architecture"][written] = True
        """
        def _set(d: dict) -> None:
            # docs and per-key sub-dict created on demand.
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["written"] = written

        self._base.update(_set)

    def set_doc_path(self, doc_key: str, path: str) -> None:
        """
        Record the canonical path for *doc_key*.

        Args:
            doc_key (str): Identifier of the doc entry.
            path (str): Absolute or workflow-relative path.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[docs][doc_key][path].

        Example:
            >>> store.specs.set_doc_path("architecture", "/tmp/arch.md")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[docs]["architecture"][path] = "/tmp/arch.md"
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["path"] = path

        self._base.update(_set)

    def set_doc_md_path(self, doc_key: str, path: str) -> None:
        """
        Record the markdown path for *doc_key*.

        Used when the doc is stored as an ``.md`` / ``.json`` pair — keeps
        the two paths under a single doc entry.

        Args:
            doc_key (str): Identifier of the doc entry.
            path (str): Path to the ``.md`` file.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[docs][doc_key][md_path].

        Example:
            >>> store.specs.set_doc_md_path("architecture", "/tmp/arch.md")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[docs]["architecture"][md_path] = "/tmp/arch.md"
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["md_path"] = path

        self._base.update(_set)

    def set_doc_json_path(self, doc_key: str, path: str) -> None:
        """
        Record the JSON path for *doc_key*.

        Used when the doc is stored as an ``.md`` / ``.json`` pair.

        Args:
            doc_key (str): Identifier of the doc entry.
            path (str): Path to the ``.json`` file.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[docs][doc_key][json_path].

        Example:
            >>> store.specs.set_doc_json_path("architecture", "/tmp/arch.json")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[docs]["architecture"][json_path] = "/tmp/arch.json"
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["json_path"] = path

        self._base.update(_set)

    def is_doc_written(self, doc_key: str) -> bool:
        """
        Check whether the ``written`` flag for *doc_key* has been set.

        Args:
            doc_key (str): Identifier of the doc entry.

        Returns:
            bool: ``True`` when the doc is marked written.

        Example:
            >>> store.specs.is_doc_written("architecture")  # doctest: +SKIP
            Return: True
        """
        # Defensive .get chain — docs/doc_key sub-dicts may not exist.
        return self.docs.get(doc_key, {}).get("written", False)
