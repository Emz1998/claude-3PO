#!/usr/bin/env python3
"""
Unit tests for .claude/hooks/file_lock/session_cleanup.py

session_cleanup.py is the SessionEnd hook that releases ALL locks still held
by the current session. It reads the per-session registry, force-releases every
SoftFileLock listed in it, deletes each .lock file, then removes the registry
itself — preventing stale locks from blocking future sessions after a crash or
abrupt termination.

Coverage:
  - main() with no registry     : exits 0 silently
  - main() with one lock        : releases it and removes registry
  - main() with multiple locks  : releases all and removes registry
  - main() with missing lock files : handles missing_ok gracefully
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

# Make the file_lock package importable without installing it
sys.path.insert(0, str(Path(__file__).parent.parent / "file_lock"))

import session_cleanup as sc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_registry(lock_dir: Path, session_id: str, entries: list[str]) -> Path:
    """Write a registry file and return its path.

    Args:
        lock_dir: Directory that holds lock files and registries.
        session_id: Session identifier used as the registry filename prefix.
        entries: List of lock-file path strings to store in the registry.

    Returns:
        Path to the written registry file.
    """
    registry = lock_dir / f"{session_id}.registry"
    registry.write_text(json.dumps(entries))
    return registry


def _run_main(monkeypatch, tmp_path, session_id: str = "test-session") -> int:
    """Patch LOCK_DIR / SESSION_ID, run main(), and return the exit code.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        tmp_path: Isolated temp directory used as LOCK_DIR root.
        session_id: Simulated CLAUDE_SESSION_ID value.

    Returns:
        Integer exit code from SystemExit.
    """
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(sc, "LOCK_DIR", lock_dir)
    monkeypatch.setattr(sc, "SESSION_ID", session_id)

    with pytest.raises(SystemExit) as exc_info:
        sc.main()

    return exc_info.value.code


# ---------------------------------------------------------------------------
# main() — no registry
# ---------------------------------------------------------------------------

class TestMainNoRegistry:
    """When no registry file exists for the session there is nothing to clean up."""

    def test_exits_0_without_registry(self, monkeypatch, tmp_path):
        """No registry → exit 0 immediately, no errors raised."""
        code = _run_main(monkeypatch, tmp_path, session_id="sess-no-reg")
        assert code == 0


# ---------------------------------------------------------------------------
# main() — single lock
# ---------------------------------------------------------------------------

class TestMainSingleLock:
    """Cleanup of a session that held exactly one lock."""

    def test_releases_the_lock(self, monkeypatch, tmp_path):
        """SoftFileLock.release(force=True) must be called for the held lock."""
        session_id = "sess-single"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        lock_file = lock_dir / "src_app.py.lock"
        lock_file.touch()
        _make_registry(lock_dir, session_id, [str(lock_file)])

        mock_lock = MagicMock()
        with patch("session_cleanup.SoftFileLock", return_value=mock_lock):
            _run_main(monkeypatch, tmp_path, session_id=session_id)

        mock_lock.release.assert_called_once_with(force=True)

    def test_deletes_lock_file(self, monkeypatch, tmp_path):
        """The .lock file must be removed from disk after release."""
        session_id = "sess-del-lock"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        lock_file = lock_dir / "src_app.py.lock"
        lock_file.touch()
        _make_registry(lock_dir, session_id, [str(lock_file)])

        with patch("session_cleanup.SoftFileLock", return_value=MagicMock()):
            _run_main(monkeypatch, tmp_path, session_id=session_id)

        assert not lock_file.exists()

    def test_deletes_registry(self, monkeypatch, tmp_path):
        """The registry file must be deleted once all locks are released."""
        session_id = "sess-del-reg"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        lock_file = lock_dir / "src_app.py.lock"
        lock_file.touch()
        registry = _make_registry(lock_dir, session_id, [str(lock_file)])

        with patch("session_cleanup.SoftFileLock", return_value=MagicMock()):
            _run_main(monkeypatch, tmp_path, session_id=session_id)

        assert not registry.exists()

    def test_exits_0_on_success(self, monkeypatch, tmp_path):
        """Successful cleanup must exit 0."""
        session_id = "sess-exit-0"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        lock_file = lock_dir / "out.txt.lock"
        lock_file.touch()
        _make_registry(lock_dir, session_id, [str(lock_file)])

        with patch("session_cleanup.SoftFileLock", return_value=MagicMock()):
            code = _run_main(monkeypatch, tmp_path, session_id=session_id)

        assert code == 0


# ---------------------------------------------------------------------------
# main() — multiple locks
# ---------------------------------------------------------------------------

class TestMainMultipleLocks:
    """Cleanup of a session that held several locks simultaneously."""

    def test_releases_all_locks(self, monkeypatch, tmp_path):
        """Every lock in the registry must be force-released."""
        session_id = "sess-multi"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        lock_files = [lock_dir / f"file_{i}.lock" for i in range(3)]
        for lf in lock_files:
            lf.touch()
        _make_registry(lock_dir, session_id, [str(lf) for lf in lock_files])

        mock_lock = MagicMock()
        with patch("session_cleanup.SoftFileLock", return_value=mock_lock):
            _run_main(monkeypatch, tmp_path, session_id=session_id)

        # release(force=True) called once per lock
        assert mock_lock.release.call_count == len(lock_files)
        for release_call in mock_lock.release.call_args_list:
            assert release_call == call(force=True)

    def test_deletes_all_lock_files(self, monkeypatch, tmp_path):
        """All .lock files must be removed from disk, not just the first one."""
        session_id = "sess-multi-del"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        lock_files = [lock_dir / f"file_{i}.lock" for i in range(3)]
        for lf in lock_files:
            lf.touch()
        _make_registry(lock_dir, session_id, [str(lf) for lf in lock_files])

        with patch("session_cleanup.SoftFileLock", return_value=MagicMock()):
            _run_main(monkeypatch, tmp_path, session_id=session_id)

        for lf in lock_files:
            assert not lf.exists(), f"{lf.name} should have been deleted"

    def test_deletes_registry_after_all_releases(self, monkeypatch, tmp_path):
        """Registry must be deleted once all locks are released, even with multiple entries."""
        session_id = "sess-multi-reg"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        lock_files = [lock_dir / f"x_{i}.lock" for i in range(2)]
        for lf in lock_files:
            lf.touch()
        registry = _make_registry(lock_dir, session_id, [str(lf) for lf in lock_files])

        with patch("session_cleanup.SoftFileLock", return_value=MagicMock()):
            _run_main(monkeypatch, tmp_path, session_id=session_id)

        assert not registry.exists()


# ---------------------------------------------------------------------------
# main() — missing lock files (crash / manual deletion)
# ---------------------------------------------------------------------------

class TestMainMissingLockFiles:
    """Handles sessions where .lock files were deleted externally before cleanup ran."""

    def test_missing_lock_file_does_not_raise(self, monkeypatch, tmp_path):
        """unlink(missing_ok=True) means an already-deleted lock file must not crash cleanup."""
        session_id = "sess-missing"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        # Register a lock path that does NOT exist on disk
        ghost_lock = lock_dir / "ghost.lock"
        _make_registry(lock_dir, session_id, [str(ghost_lock)])

        with patch("session_cleanup.SoftFileLock", return_value=MagicMock()):
            code = _run_main(monkeypatch, tmp_path, session_id=session_id)

        # Must still exit cleanly
        assert code == 0

    def test_registry_still_deleted_when_lock_files_missing(self, monkeypatch, tmp_path):
        """Registry must be cleaned up even when .lock files were already gone."""
        session_id = "sess-ghost-reg"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        ghost_lock = lock_dir / "ghost.lock"
        registry = _make_registry(lock_dir, session_id, [str(ghost_lock)])

        with patch("session_cleanup.SoftFileLock", return_value=MagicMock()):
            _run_main(monkeypatch, tmp_path, session_id=session_id)

        assert not registry.exists()
