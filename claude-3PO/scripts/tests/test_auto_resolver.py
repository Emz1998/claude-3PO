"""Tests for utils/auto_resolver.py — watchdog → resolve(...) glue.

Verifies the handler's contract without relying on a real filesystem
watch loop: we instantiate ``AutoResolverHandler`` directly, hand it a
synthesized ``FileModifiedEvent`` for the configured ``state.json``,
and confirm it constructs the expected StateStore / Config and calls
``resolver.resolve`` exactly once.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from watchdog.events import FileModifiedEvent

from utils.auto_resolver import AutoResolver, AutoResolverHandler
from lib.state_store import StateStore


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    # Seed with a minimal valid body so StateStore(state_path).load() succeeds.
    p = tmp_path / "state.json"
    p.write_text(json.dumps({"session_id": "auto-1", "workflow_active": True}))
    return p


class TestAutoResolverHandler:
    """The on_modified handler invokes resolve(config, state) on matching events."""

    def test_modify_triggers_resolve_once(self, state_path: Path):
        # Synthesize the watchdog event the observer would normally deliver.
        with patch("utils.auto_resolver.resolve") as mock_resolve:
            handler = AutoResolverHandler(state_path)
            handler.on_modified(FileModifiedEvent(str(state_path)))

            assert mock_resolve.call_count == 1

    def test_resolve_receives_state_store_bound_to_path(self, state_path: Path):
        # The state passed into resolve must read from *our* state.json.
        with patch("utils.auto_resolver.resolve") as mock_resolve:
            handler = AutoResolverHandler(state_path)
            handler.on_modified(FileModifiedEvent(str(state_path)))

            _config, state = mock_resolve.call_args.args
            assert isinstance(state, StateStore)
            assert state._path == state_path

    def test_unrelated_path_is_ignored(self, state_path: Path, tmp_path: Path):
        # Events for sibling files in the same dir must not trigger resolve.
        other = tmp_path / "other.json"
        other.write_text("{}")
        with patch("utils.auto_resolver.resolve") as mock_resolve:
            handler = AutoResolverHandler(state_path)
            handler.on_modified(FileModifiedEvent(str(other)))

            mock_resolve.assert_not_called()

    def test_directory_event_is_ignored(self, state_path: Path):
        # Watchdog fires directory events too — those should be filtered.
        with patch("utils.auto_resolver.resolve") as mock_resolve:
            handler = AutoResolverHandler(state_path)
            event = FileModifiedEvent(str(state_path.parent))
            event.is_directory = True
            handler.on_modified(event)

            mock_resolve.assert_not_called()


class TestAutoResolverWiring:
    """The AutoResolver glue wires the observer to the parent directory."""

    def test_constructs_handler_with_resolved_path(self, state_path: Path):
        # Default construction should hand the handler the absolute state path.
        resolver = AutoResolver(state_path)
        assert resolver.handler.state_path == state_path

    def test_observer_starts_and_stops_cleanly(self, state_path: Path):
        # Smoke-test the start/stop lifecycle so dropped joins don't deadlock.
        resolver = AutoResolver(state_path)
        resolver.start()
        try:
            assert resolver.observer.is_alive()
        finally:
            resolver.stop()
        assert not resolver.observer.is_alive()
