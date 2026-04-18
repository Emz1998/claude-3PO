"""Tests for :class:`BuildState` — the build-workflow slice of StateStore.

Exercises the five build-only accessors (created_tasks, add_created_task,
get_clarify_phase, set_clarify_session, bump_clarify_iteration) and
confirms they delegate through the shared :class:`BaseState` so reads from
the facade see the same JSONL line that the slice wrote.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.state_store import StateStore


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    # Fresh StateStore per test; no default state so we start empty.
    return StateStore(tmp_path / "state.jsonl", session_id="s")


class TestBuildCreatedTasks:
    """created_tasks / add_created_task round-trip through the shared base."""

    def test_default_empty(self, store: StateStore):
        assert store.build.created_tasks == []

    def test_add_persists_through_base(self, store: StateStore):
        # Write via the slice, confirm it landed on the shared JSONL line.
        store.build.add_created_task("Build login")
        assert store.build.created_tasks == ["Build login"]
        assert store.load()["created_tasks"] == ["Build login"]

    def test_add_deduplicates(self, store: StateStore):
        store.build.add_created_task("x")
        store.build.add_created_task("x")
        assert store.build.created_tasks == ["x"]


class TestBuildClarifyPhase:
    """Clarify-phase helpers mutate state.phases through the shared base."""

    def test_get_clarify_phase_none_initially(self, store: StateStore):
        assert store.build.get_clarify_phase() is None

    def test_set_clarify_session_persists(self, store: StateStore):
        # Phase must exist before the clarify helpers can find it.
        store.add_phase("clarify")
        store.build.set_clarify_session("sess-xyz")
        phase = store.build.get_clarify_phase()
        assert phase["headless_session_id"] == "sess-xyz"
        assert phase["iteration_count"] == 0

    def test_bump_clarify_iteration_increments(self, store: StateStore):
        store.add_phase("clarify")
        store.build.set_clarify_session("sess-xyz")
        store.build.bump_clarify_iteration()
        store.build.bump_clarify_iteration()
        assert store.build.get_clarify_phase()["iteration_count"] == 2

    def test_bump_clarify_iteration_noop_without_phase(self, store: StateStore):
        # No clarify phase present → silent no-op per docstring contract.
        store.build.bump_clarify_iteration()
        assert store.build.get_clarify_phase() is None


class TestBuildSliceSharesBase:
    """Writes through the slice are visible via the facade and the base."""

    def test_slice_write_visible_through_facade(self, store: StateStore):
        store.build.add_created_task("alpha")
        # Same JSONL line — facade sees what the slice wrote.
        assert "alpha" in store.load()["created_tasks"]
