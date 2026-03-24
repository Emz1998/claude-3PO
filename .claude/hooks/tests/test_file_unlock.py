#!/usr/bin/env python3
"""
Unit tests for .claude/hooks/file_lock/file_unlock.py

file_unlock.py is the PostToolUse counterpart to file_lock.py.
After Claude Code finishes a Write/Edit/MultiEdit/NotebookEdit tool call it
reads the per-session registry, finds the lock that corresponds to the just-
edited file, releases it via SoftFileLock.release(force=True), deletes the
.lock file, and removes the entry from the registry.

Coverage:
  - release_lock()  : releases one lock file and removes it from disk
  - main()          : full hook flow — skip conditions, registry update, cleanup
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

# Make the file_lock package importable without installing it
sys.path.insert(0, str(Path(__file__).parent.parent))

from file_unlock import file_unlock as fu  # type: ignore


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


# ---------------------------------------------------------------------------
# release_lock — releases one SoftFileLock and deletes the .lock file
# ---------------------------------------------------------------------------


class TestReleaseLock:
    """Tests for release_lock(), which performs a forced release of a single
    SoftFileLock and removes the backing .lock file from disk."""

    def test_releases_soft_file_lock(self, tmp_path):
        """SoftFileLock.release(force=True) must be called for the given path."""
        lock_file = tmp_path / "some_file.lock"
        lock_file.touch()  # simulate an existing lock file

        mock_lock = MagicMock()
        with patch("file_unlock.SoftFileLock", return_value=mock_lock) as mock_cls:
            fu.release_lock(str(lock_file))

        # Verify SoftFileLock was constructed with the correct path
        mock_cls.assert_called_once_with(lock_file)
        mock_lock.release.assert_called_once_with(force=True)

    def test_deletes_lock_file(self, tmp_path):
        """The .lock file must be removed from disk after release."""
        lock_file = tmp_path / "some_file.lock"
        lock_file.touch()

        with patch("file_unlock.SoftFileLock", return_value=MagicMock()):
            fu.release_lock(str(lock_file))

        assert not lock_file.exists()

    def test_missing_lock_file_does_not_raise(self, tmp_path):
        """release_lock must not raise even when the .lock file is already gone
        (uses unlink(missing_ok=True) so double-release is safe)."""
        lock_file = tmp_path / "already_gone.lock"
        # file intentionally NOT created

        with patch("file_unlock.SoftFileLock", return_value=MagicMock()):
            fu.release_lock(str(lock_file))  # must not raise


# ---------------------------------------------------------------------------
# main() — full hook flow
# ---------------------------------------------------------------------------


class TestMain:
    """Integration-style tests for main(), which reads a PostToolUse event from
    stdin and releases the lock that was acquired for that file."""

    def _run_main(
        self,
        stdin_data: dict,
        monkeypatch,
        tmp_path,
        session_id: str = "test-session",
    ):
        """Wire up dependencies and run main().

        Args:
            stdin_data: The hook event payload sent by Claude Code.
            monkeypatch: pytest monkeypatch fixture.
            tmp_path: Isolated temp directory used as LOCK_DIR root.
            session_id: Simulated CLAUDE_SESSION_ID value.

        Returns:
            Exit code raised via SystemExit.
        """
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(fu, "LOCK_DIR", lock_dir)
        monkeypatch.setattr(fu, "SESSION_ID", session_id)

        import io

        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(stdin_data)))

        with pytest.raises(SystemExit) as exc_info:
            fu.main()

        return exc_info.value.code

    # --- early-exit paths ---

    def test_non_locking_tool_exits_0(self, monkeypatch, tmp_path):
        """Tools not in LOCKING_TOOLS must be ignored with exit 0."""
        code = self._run_main(
            {"tool_name": "Read", "tool_input": {"file_path": "/foo.py"}},
            monkeypatch,
            tmp_path,
        )
        assert code == 0

    def test_missing_file_path_exits_0(self, monkeypatch, tmp_path):
        """A locking tool with no resolvable file path must exit 0 without touching registry."""
        code = self._run_main(
            {"tool_name": "Write", "tool_input": {}},
            monkeypatch,
            tmp_path,
        )
        assert code == 0

    def test_no_registry_exits_0(self, monkeypatch, tmp_path):
        """If the session registry doesn't exist, there's nothing to release — exit 0."""
        code = self._run_main(
            {"tool_name": "Write", "tool_input": {"file_path": "/src/app.py"}},
            monkeypatch,
            tmp_path,
        )
        assert code == 0

    # --- lock release ---

    def test_matching_lock_is_released(self, monkeypatch, tmp_path):
        """When the registry contains the target lock, it must be released."""
        session_id = "sess-release"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        # Create the lock file that should be released
        safe = "src_app.py"
        lock_file = lock_dir / f"{safe}.lock"
        lock_file.touch()

        _make_registry(lock_dir, session_id, [str(lock_file)])

        mock_lock = MagicMock()
        with patch("file_unlock.SoftFileLock", return_value=mock_lock):
            self._run_main(
                {"tool_name": "Write", "tool_input": {"file_path": "/src/app.py"}},
                monkeypatch,
                tmp_path,
                session_id=session_id,
            )

        mock_lock.release.assert_called_once_with(force=True)

    def test_registry_entry_removed_after_release(self, monkeypatch, tmp_path):
        """The released lock's path must be removed from the registry file."""
        session_id = "sess-remove-entry"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        safe = "tmp_out.txt"
        lock_file = lock_dir / f"{safe}.lock"
        lock_file.touch()

        registry = _make_registry(lock_dir, session_id, [str(lock_file)])

        with patch("file_unlock.SoftFileLock", return_value=MagicMock()):
            self._run_main(
                {"tool_name": "Edit", "tool_input": {"file_path": "/tmp/out.txt"}},
                monkeypatch,
                tmp_path,
                session_id=session_id,
            )

        # Registry should be deleted when it becomes empty
        assert not registry.exists()

    def test_registry_deleted_when_empty(self, monkeypatch, tmp_path):
        """When all locks are released the registry file itself must be deleted."""
        session_id = "sess-empty-reg"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        safe = "src_only.py"
        lock_file = lock_dir / f"{safe}.lock"
        lock_file.touch()

        registry = _make_registry(lock_dir, session_id, [str(lock_file)])

        with patch("file_unlock.SoftFileLock", return_value=MagicMock()):
            self._run_main(
                {"tool_name": "Write", "tool_input": {"file_path": "/src/only.py"}},
                monkeypatch,
                tmp_path,
                session_id=session_id,
            )

        assert not registry.exists()

    def test_other_locks_remain_in_registry(self, monkeypatch, tmp_path):
        """Releasing one lock must leave unrelated locks untouched in the registry."""
        session_id = "sess-partial"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        # Two lock files; only one should be released
        lock_a = lock_dir / "src_a.py.lock"
        lock_b = lock_dir / "src_b.py.lock"
        lock_a.touch()
        lock_b.touch()

        registry = _make_registry(lock_dir, session_id, [str(lock_a), str(lock_b)])

        with patch("file_unlock.SoftFileLock", return_value=MagicMock()):
            self._run_main(
                {"tool_name": "Write", "tool_input": {"file_path": "/src/a.py"}},
                monkeypatch,
                tmp_path,
                session_id=session_id,
            )

        # Registry still exists and still contains lock_b
        assert registry.exists()
        remaining = json.loads(registry.read_text())
        assert str(lock_b) in remaining
        assert str(lock_a) not in remaining

    @pytest.mark.parametrize(
        "tool_name", ["Write", "Edit", "MultiEdit", "NotebookEdit"]
    )
    def test_all_locking_tools_trigger_release(self, tool_name, monkeypatch, tmp_path):
        """All four locking tools must attempt to release a lock when one exists."""
        session_id = f"sess-{tool_name.lower()}"
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        input_key = "notebook_path" if tool_name == "NotebookEdit" else "file_path"
        file_path = f"/tmp/{tool_name}.py"

        safe = file_path.replace("/", "_").replace("\\", "_").strip("_")
        lock_file = lock_dir / f"{safe}.lock"
        lock_file.touch()

        _make_registry(lock_dir, session_id, [str(lock_file)])

        mock_lock = MagicMock()
        with patch("file_unlock.SoftFileLock", return_value=mock_lock):
            code = self._run_main(
                {"tool_name": tool_name, "tool_input": {input_key: file_path}},
                monkeypatch,
                tmp_path,
                session_id=session_id,
            )

        assert code == 0
        mock_lock.release.assert_called_once_with(force=True)
