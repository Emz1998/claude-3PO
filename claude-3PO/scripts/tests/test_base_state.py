"""Tests for :class:`BaseState` and the :class:`StateStore` facade composition.

These tests prove the slice-1 invariants:

1. :class:`BaseState` instantiates standalone (no facade required) and its
   shared-method surface round-trips through the single ``state.json`` file.
2. The facade :class:`StateStore` exposes the three workflow slices as
   explicit named sub-attributes that are always present (workflow-agnostic).
3. All slices share a single :class:`BaseState` — one file, one lock — so a
   write through one slice is visible through every other accessor.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.state_store import (
    BaseState,
    BuildState,
    ImplementState,
    SpecsState,
    StateStore,
)


class TestBaseStateStandalone:
    """:class:`BaseState` works without the StateStore facade around it."""

    def test_instantiation_standalone(self, tmp_path: Path):
        # Confirms BaseState is usable as a plain object (no facade required).
        path = tmp_path / "state.json"
        base = BaseState(path)
        assert base.load() == {}

    def test_shared_method_round_trip(self, tmp_path: Path):
        # Exercises load -> set -> load through the public shared surface.
        path = tmp_path / "state.json"
        base = BaseState(path, default_state={"foo": 0})
        base.set("foo", 42)
        assert base.load()["foo"] == 42


class TestStateStoreFacade:
    """:class:`StateStore` exposes every workflow slice regardless of type."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> StateStore:
        # Fresh StateStore per test — no prior workflow_type set.
        return StateStore(tmp_path / "state.json")

    def test_slices_are_named_sub_attrs(self, store: StateStore):
        # Explicit named sub-attrs — no __getattr__ fallback.
        assert isinstance(store.build, BuildState)
        assert isinstance(store.implement, ImplementState)
        assert isinstance(store.specs, SpecsState)

    def test_slices_present_for_every_workflow_type(self, tmp_path: Path):
        # All three slices exist regardless of workflow_type (facade is agnostic).
        for wf in ("build", "implement", "specs"):
            store = StateStore(
                tmp_path / f"{wf}.json",
                default_state={"workflow_type": wf},
            )
            assert store.build is not None
            assert store.implement is not None
            assert store.specs is not None

    def test_shared_methods_reachable_on_facade(self, store: StateStore):
        # Facade inherits BaseState → shared accessors unchanged for callers.
        store.set("foo", "bar")
        assert store.get("foo") == "bar"
        assert store.phases == []
        assert store.agents == []


class TestSharedFileAndLock:
    """All slices share one :class:`BaseState` — one file, one lock."""

    def test_slices_share_base_reference(self, tmp_path: Path):
        # Ownership test: every slice's _base is the owning StateStore.
        store = StateStore(tmp_path / "state.json")
        assert store.build._base is store
        assert store.implement._base is store
        assert store.specs._base is store

    def test_write_through_base_visible_to_slices(self, tmp_path: Path):
        # Slice wrappers read through _base so any write is visible everywhere.
        store = StateStore(tmp_path / "state.json")
        store.set("marker", "hello")
        assert store.build._base.load()["marker"] == "hello"
        assert store.implement._base.load()["marker"] == "hello"
        assert store.specs._base.load()["marker"] == "hello"

    def test_single_json_document(self, tmp_path: Path):
        # Two writes through the facade should produce one JSON document on disk.
        path = tmp_path / "state.json"
        store = StateStore(path)
        store.set("a", 1)
        store.set("b", 2)
        payload = json.loads(path.read_text())
        assert payload["a"] == 1 and payload["b"] == 2
