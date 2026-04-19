"""Tests for :class:`SpecsState` — specs-workflow slice of StateStore.

Exercises the six specs-only accessors (docs, set_doc_written, set_doc_path,
set_doc_md_path, set_doc_json_path, is_doc_written) and confirms they
delegate through the shared :class:`BaseState`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.state_store import StateStore


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    # Fresh StateStore per test; no default state so we start empty.
    return StateStore(tmp_path / "state.json")


class TestSpecsDocs:
    """docs / set_doc_written round-trip through the shared base."""

    def test_default_empty(self, store: StateStore):
        assert store.specs.docs == {}

    def test_set_doc_written_persists(self, store: StateStore):
        store.specs.set_doc_written("arch", True)
        # Slice reads flow back through the shared JSON document.
        assert store.specs.docs["arch"]["written"] is True
        assert store.load()["docs"]["arch"]["written"] is True

    def test_is_doc_written(self, store: StateStore):
        assert store.specs.is_doc_written("arch") is False
        store.specs.set_doc_written("arch", True)
        assert store.specs.is_doc_written("arch") is True


class TestSpecsDocPaths:
    """path / md_path / json_path setters all land under the same doc entry."""

    def test_set_doc_path(self, store: StateStore):
        store.specs.set_doc_path("arch", "/tmp/arch.md")
        assert store.specs.docs["arch"]["path"] == "/tmp/arch.md"

    def test_set_doc_md_and_json_path_coexist(self, store: StateStore):
        # Paired .md / .json under one doc_key — both keys must survive.
        store.specs.set_doc_md_path("backlog", "/tmp/b.md")
        store.specs.set_doc_json_path("backlog", "/tmp/b.json")
        entry = store.specs.docs["backlog"]
        assert entry["md_path"] == "/tmp/b.md"
        assert entry["json_path"] == "/tmp/b.json"


class TestSpecsSliceSharesBase:
    """Writes through the slice are visible via the facade and the base."""

    def test_slice_write_visible_through_facade(self, store: StateStore):
        store.specs.set_doc_written("vision", True)
        # Same JSON document — facade sees what the slice wrote.
        assert store.load()["docs"]["vision"]["written"] is True
