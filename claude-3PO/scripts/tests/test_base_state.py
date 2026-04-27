"""Tests for :class:`BaseState` and the :class:`StateStore` facade composition.

These tests prove the slice invariants:

1. :class:`BaseState` instantiates standalone (no facade required) and its
   shared-method surface round-trips through the single ``state.json`` file.
2. The facade :class:`StateStore` exposes the implement workflow slice as
   an explicit named sub-attribute.
3. The slice shares a single :class:`BaseState` — one file, one lock — so a
   write through one path is visible through every other accessor.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.state_store import (
    BaseState,
    ImplementState,
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
    """:class:`StateStore` exposes the implement workflow slice."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> StateStore:
        # Fresh StateStore per test — no prior workflow_type set.
        return StateStore(tmp_path / "state.json")

    def test_implement_slice_is_named_sub_attr(self, store: StateStore):
        # Explicit named sub-attr — no __getattr__ fallback.
        assert isinstance(store.implement, ImplementState)

    def test_legacy_slices_removed(self, store: StateStore):
        # build / specs slices are gone after the implement-only refactor.
        assert not hasattr(store, "build")
        assert not hasattr(store, "specs")

    def test_shared_methods_reachable_on_facade(self, store: StateStore):
        # Facade inherits BaseState → shared accessors unchanged for callers.
        store.set("foo", "bar")
        assert store.get("foo") == "bar"
        assert store.phases == []
        assert store.agents == []


class TestSharedFileAndLock:
    """The implement slice shares one :class:`BaseState` — one file, one lock."""

    def test_slice_shares_base_reference(self, tmp_path: Path):
        # Ownership test: implement slice's _base is the owning StateStore.
        store = StateStore(tmp_path / "state.json")
        assert store.implement._base is store

    def test_write_through_base_visible_to_slice(self, tmp_path: Path):
        # Slice wrappers read through _base so any write is visible everywhere.
        store = StateStore(tmp_path / "state.json")
        store.set("marker", "hello")
        assert store.implement._base.load()["marker"] == "hello"

    def test_single_json_document(self, tmp_path: Path):
        # Two writes through the facade should produce one JSON document on disk.
        path = tmp_path / "state.json"
        store = StateStore(path)
        store.set("a", 1)
        store.set("b", 2)
        payload = json.loads(path.read_text())
        assert payload["a"] == 1 and payload["b"] == 2


class TestNoOpWriteDetection:
    """``update`` should skip the disk write when the mutator doesn't change the state."""

    def _instrument_writes(self, base: BaseState) -> list[dict]:
        writes: list[dict] = []
        original = base._write

        def _recording(data: dict) -> None:
            writes.append(dict(data))
            original(data)

        base._write = _recording  # type: ignore[method-assign]
        return writes

    def test_noop_update_does_not_rewrite_file(self, tmp_path: Path):
        base = BaseState(tmp_path / "state.json", default_state={"k": 1})
        base.update(lambda d: d.setdefault("k", 1))
        writes = self._instrument_writes(base)
        base.update(lambda d: d.setdefault("k", 1))
        assert writes == []

    def test_real_change_does_rewrite_file(self, tmp_path: Path):
        base = BaseState(tmp_path / "state.json", default_state={"k": 1})
        base.update(lambda d: d.update({"k": 1}))
        writes = self._instrument_writes(base)
        base.update(lambda d: d.update({"k": 2}))
        assert len(writes) == 1 and writes[0]["k"] == 2
