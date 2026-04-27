"""Tests for project_manager.watcher — file watcher + auto-resolve + auto-sync."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from project_manager import watcher as w


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def backlog_file(tmp_path):
    # Minimal backlog with one Backlog story that Rule A will promote on
    # the first resolve pass — lets us observe the watcher end-to-end.
    p = tmp_path / "project.json"
    p.write_text(
        json.dumps(
            {
                "project": "T",
                "goal": "",
                "stories": [
                    {"id": "SK-1", "status": "Backlog", "blocked_by": [], "tasks": []},
                ],
            }
        ),
        encoding="utf-8",
    )
    return p


@pytest.fixture
def mock_syncer():
    with patch.object(w, "Syncer") as klass:
        instance = MagicMock()
        klass.return_value = instance
        yield instance


# ---------------------------------------------------------------------------
# ProjectWatcher.process_once — the core loop step
# ---------------------------------------------------------------------------


class TestProcessOnce:
    def test_invokes_resolver_and_saves_when_changed(self, backlog_file, mock_syncer):
        pw = w.ProjectWatcher(backlog_file)
        pw.process_once()
        # Backlog promoted → file rewritten with Ready.
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert data["stories"][0]["status"] == "Ready"

    def test_calls_syncer_on_change(self, backlog_file, mock_syncer):
        pw = w.ProjectWatcher(backlog_file)
        pw.process_once()
        mock_syncer.run.assert_called_once_with("sync")

    def test_self_write_is_deduped(self, backlog_file, mock_syncer):
        pw = w.ProjectWatcher(backlog_file)
        # Pre-seed the hash to match current file contents — simulates the
        # watcher having just written this state itself.
        pw._last_processed_hash = pw._hash_file()
        pw.process_once()
        mock_syncer.run.assert_not_called()

    def test_syncer_failure_does_not_propagate(self, backlog_file, mock_syncer):
        mock_syncer.run.side_effect = RuntimeError("gh down")
        pw = w.ProjectWatcher(backlog_file)
        # Must not raise — sync failures are logged and swallowed so the
        # watcher keeps running.
        pw.process_once()

    def test_records_hash_after_processing(self, backlog_file, mock_syncer):
        pw = w.ProjectWatcher(backlog_file)
        pw.process_once()
        # Hash now equals the post-write contents; a second process_once
        # with no external edit must be a no-op.
        mock_syncer.run.reset_mock()
        pw.process_once()
        mock_syncer.run.assert_not_called()

    def test_no_resolver_change_still_syncs(self, tmp_path, mock_syncer):
        # Backlog that is already converged — resolver returns False, but
        # the plan says "always sync after a non-skipped event".
        p = tmp_path / "project.json"
        p.write_text(
            json.dumps(
                {"stories": [{"id": "SK-1", "status": "Ready",
                              "blocked_by": [], "tasks": []}]}
            ),
            encoding="utf-8",
        )
        pw = w.ProjectWatcher(p)
        pw.process_once()
        mock_syncer.run.assert_called_once_with("sync")


# ---------------------------------------------------------------------------
# Debounce — collapse editor save bursts
# ---------------------------------------------------------------------------


class TestDebounce:
    def test_rapid_events_collapse_to_one_process(
        self, backlog_file, mock_syncer, monkeypatch
    ):
        # Patch process_once so we can count invocations without touching
        # the resolver/syncer logic already exercised above.
        calls = []
        pw = w.ProjectWatcher(backlog_file, debounce_seconds=0.05)
        monkeypatch.setattr(pw, "process_once", lambda: calls.append(1))
        # Fire three events in quick succession — should still produce
        # exactly one debounced call.
        for _ in range(3):
            pw._schedule_process()
        time.sleep(0.2)
        assert len(calls) == 1

    def test_handler_filters_unrelated_paths(
        self, backlog_file, mock_syncer, monkeypatch
    ):
        # A modify event on a sibling file must NOT trigger a resolve.
        pw = w.ProjectWatcher(backlog_file, debounce_seconds=0.05)
        calls = []
        monkeypatch.setattr(pw, "process_once", lambda: calls.append(1))
        sibling = MagicMock(is_directory=False, src_path=str(backlog_file.parent / "other.json"))
        pw.handler.on_modified(sibling)
        time.sleep(0.15)
        assert calls == []

    def test_handler_ignores_directory_events(self, backlog_file, mock_syncer):
        pw = w.ProjectWatcher(backlog_file, debounce_seconds=0.05)
        # is_directory=True must short-circuit before scheduling.
        pw.handler.on_modified(MagicMock(is_directory=True, src_path=str(backlog_file)))
        assert pw._timer is None or not pw._timer.is_alive()


# ---------------------------------------------------------------------------
# Reentrancy — concurrent process_once must serialize
# ---------------------------------------------------------------------------


class TestInitialSync:
    def test_main_runs_initial_sync_on_startup(self, backlog_file, monkeypatch):
        # Edits made to project.json while the watcher was off must reach
        # GitHub on the next launch. An unconditional process_once() right
        # after observer.start() converges state before blocking on events.
        import argparse

        fake_pw = MagicMock()
        monkeypatch.setattr(w, "ProjectWatcher", lambda *_a, **_k: fake_pw)
        # Skip the blocking signal.pause(); we only care about startup calls.
        monkeypatch.setattr(w.signal, "pause", lambda: None)
        monkeypatch.setattr(w.signal, "signal", lambda *_a, **_k: None)

        ns = argparse.Namespace(
            backlog_path=str(backlog_file), repo=None, project=None, owner=None,
        )
        assert w.main_from_args(ns) == 0
        fake_pw.start.assert_called_once()
        fake_pw.process_once.assert_called_once()
        # Observer must be started before the initial sync so a file change
        # that lands during the sync is captured rather than dropped.
        assert (
            fake_pw.method_calls.index(("start", (), {}))
            < fake_pw.method_calls.index(("process_once", (), {}))
        )


class TestProcessOnceReentrancy:
    def test_concurrent_call_returns_without_syncing(
        self, backlog_file, mock_syncer
    ):
        # Simulate: watcher writes file mid-sync → watchdog fires a second
        # process_once while the first is still running. Without the guard
        # this produced two concurrent syncs (the real-world bug — duplicate
        # title errors + racing GitHub writes). With the guard, the second
        # call must return immediately and NOT start another sync cycle.
        import threading

        inside_sync = threading.Event()
        release_sync = threading.Event()

        def blocking_sync(_mode):
            # Signal we're in sync, then block until the test releases us.
            inside_sync.set()
            release_sync.wait(timeout=2.0)
            return 0

        mock_syncer.run.side_effect = blocking_sync
        pw = w.ProjectWatcher(backlog_file)

        first = threading.Thread(target=pw.process_once)
        first.start()
        assert inside_sync.wait(timeout=2.0), "first call never entered sync"
        # Second process_once while the first is still syncing.
        pw.process_once()
        # Let the first one finish.
        release_sync.set()
        first.join(timeout=2.0)
        # Sync ran exactly once — the reentrant call was dropped.
        assert mock_syncer.run.call_count == 1
