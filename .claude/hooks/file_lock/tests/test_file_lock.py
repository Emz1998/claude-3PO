#!/usr/bin/env python3
"""
Unit tests for .claude/hooks/file_lock/file_lock.py

Coverage:
  - get_file_path()  : resolves file path from various tool_input key names
  - lock_path_for()  : generates a filesystem-safe lock path under LOCK_DIR
  - main()           : full hook flow — skip, acquire, metadata, registry, timeout
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Make the file_lock package importable without installing it
sys.path.insert(0, str(Path(__file__).parent.parent))

from file_lock import file_lock as fl  # type: ignore


# ---------------------------------------------------------------------------
# get_file_path — resolves the target file from tool_input
# ---------------------------------------------------------------------------


class TestGetFilePath:
    """Tests for get_file_path(), which extracts the target file path from
    a tool's input dict by checking several known key names in priority order."""

    def test_file_path_key(self):
        """Standard Write/Edit tools send 'file_path'; it must be returned as-is."""
        assert fl.get_file_path({"file_path": "/src/foo.py"}) == "/src/foo.py"

    def test_path_key(self):
        """Fallback to 'path' when 'file_path' is absent."""
        assert fl.get_file_path({"path": "/src/bar.py"}) == "/src/bar.py"

    def test_notebook_path_key(self):
        """NotebookEdit uses 'notebook_path'; it must be recognised as the target."""
        assert (
            fl.get_file_path({"notebook_path": "/notebooks/nb.ipynb"})
            == "/notebooks/nb.ipynb"
        )

    def test_file_path_takes_precedence(self):
        """'file_path' is checked first and wins over 'path' when both keys exist."""
        assert fl.get_file_path({"file_path": "/a.py", "path": "/b.py"}) == "/a.py"

    def test_missing_keys_returns_none(self):
        """An empty dict must return None so the caller can exit 0 without locking."""
        assert fl.get_file_path({}) is None

    def test_empty_string_falls_through(self):
        """An empty string is falsy, so the function should fall through to the next key."""
        assert fl.get_file_path({"file_path": "", "path": "/b.py"}) == "/b.py"


# ---------------------------------------------------------------------------
# lock_path_for — generates a safe .lock path under LOCK_DIR
# ---------------------------------------------------------------------------


class TestLockPathFor:
    """Tests for lock_path_for(), which maps a file path to a unique, filesystem-safe
    lock file path inside LOCK_DIR."""

    def test_returns_path_under_lock_dir(self, tmp_path, monkeypatch):
        """The returned lock path must be a direct child of LOCK_DIR."""
        monkeypatch.setattr(fl, "LOCK_DIR", tmp_path / "locks")
        result = fl.lock_path_for("/some/file.py")
        assert result.parent == tmp_path / "locks"
        assert result.name.endswith(".lock")

    def test_slashes_replaced(self, tmp_path, monkeypatch):
        """Forward slashes in the file path must be replaced so the name is a valid filename."""
        monkeypatch.setattr(fl, "LOCK_DIR", tmp_path / "locks")
        result = fl.lock_path_for("/a/b/c.py")
        assert "/" not in result.stem

    def test_creates_lock_dir(self, tmp_path, monkeypatch):
        """LOCK_DIR is created on demand; it must not need to pre-exist."""
        lock_dir = tmp_path / "locks"
        monkeypatch.setattr(fl, "LOCK_DIR", lock_dir)
        assert not lock_dir.exists()
        fl.lock_path_for("/some/file.py")
        assert lock_dir.exists()

    def test_different_paths_produce_different_lock_names(self, tmp_path, monkeypatch):
        """Two distinct source files must map to distinct lock paths to avoid false contention."""
        monkeypatch.setattr(fl, "LOCK_DIR", tmp_path / "locks")
        p1 = fl.lock_path_for("/a/foo.py")
        p2 = fl.lock_path_for("/b/bar.py")
        assert p1 != p2


# ---------------------------------------------------------------------------
# main() — full hook flow
# ---------------------------------------------------------------------------


class TestMain:
    """Integration-style tests for main(), which reads a hook event from stdin,
    decides whether to acquire a lock, writes metadata, updates the session registry,
    and exits with an appropriate code."""

    def _run_main(
        self, stdin_data: dict, monkeypatch, tmp_path, session_id="test-session"
    ):
        """Helper that wires up all external dependencies and runs main().

        Args:
            stdin_data: The hook event payload (normally written by Claude Code).
            monkeypatch: pytest monkeypatch fixture for patching module-level globals.
            tmp_path: Isolated temp directory used as LOCK_DIR root.
            session_id: Simulated session_id value injected into stdin_data.

        Returns:
            Tuple of (exit_code: int, captured_stdout_args: list).
        """
        monkeypatch.setattr(fl, "LOCK_DIR", tmp_path / "locks")

        payload = {"session_id": session_id, **stdin_data}

        import io

        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))

        captured_stdout = []

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "builtins.print", side_effect=lambda *a, **kw: captured_stdout.append(a)
            ):
                fl.main()

        return exc_info.value.code, captured_stdout

    # --- early-exit paths (hook should not acquire a lock) ---

    def test_non_locking_tool_exits_0(self, monkeypatch, tmp_path):
        """'Read' is not in LOCKING_TOOLS; the hook must pass through without locking."""
        code, _ = self._run_main(
            {"tool_name": "Read", "tool_input": {"file_path": "/foo.py"}},
            monkeypatch,
            tmp_path,
        )
        assert code == 0

    def test_unknown_tool_exits_0(self, monkeypatch, tmp_path):
        """Unrecognised tool names must be ignored silently with exit 0."""
        code, _ = self._run_main(
            {"tool_name": "Bash", "tool_input": {"command": "ls"}},
            monkeypatch,
            tmp_path,
        )
        assert code == 0

    def test_missing_file_path_exits_0(self, monkeypatch, tmp_path):
        """A locking tool with no resolvable file path must skip gracefully with exit 0."""
        code, _ = self._run_main(
            {"tool_name": "Write", "tool_input": {}},
            monkeypatch,
            tmp_path,
        )
        assert code == 0

    # --- successful lock acquisition ---

    def test_successful_lock_exits_0(self, monkeypatch, tmp_path):
        """Normal flow: lock acquired → exit 0 with additionalContext printed to stdout."""
        code, stdout = self._run_main(
            {"tool_name": "Write", "tool_input": {"file_path": "/src/app.py"}},
            monkeypatch,
            tmp_path,
        )
        assert code == 0
        # Claude Code reads additionalContext from stdout to surface info to the model
        output = json.loads(stdout[0][0])
        assert "additionalContext" in output
        assert "app.py" in output["additionalContext"]

    def test_lock_file_written_with_metadata(self, monkeypatch, tmp_path):
        """After acquisition the .lock file must contain session, pid, file, and timestamp."""
        session_id = "sess-abc123"
        self._run_main(
            {"tool_name": "Edit", "tool_input": {"file_path": "/src/main.py"}},
            monkeypatch,
            tmp_path,
            session_id=session_id,
        )
        lock_files = list((tmp_path / "locks").glob("*.lock"))
        assert len(lock_files) == 1

        metadata = json.loads(lock_files[0].read_text())
        assert metadata["session_id"] == session_id
        assert metadata["file"] == "/src/main.py"
        assert "pid" in metadata
        assert "acquired_at" in metadata

    def test_registry_updated(self, monkeypatch, tmp_path):
        """The per-session registry must record the lock path so cleanup hooks can release it."""
        session_id = "sess-reg-test"
        self._run_main(
            {"tool_name": "Write", "tool_input": {"file_path": "/tmp/out.txt"}},
            monkeypatch,
            tmp_path,
            session_id=session_id,
        )
        registry = tmp_path / "locks" / f"{session_id}.registry"
        assert registry.exists()
        held = json.loads(registry.read_text())
        assert len(held) == 1
        assert held[0].endswith(".lock")

    def test_registry_no_duplicates(self, monkeypatch, tmp_path):
        """Running the hook twice for the same file must not add duplicate registry entries."""
        session_id = "sess-dedup"
        for _ in range(2):
            self._run_main(
                {"tool_name": "Write", "tool_input": {"file_path": "/tmp/dup.txt"}},
                monkeypatch,
                tmp_path,
                session_id=session_id,
            )
        registry = tmp_path / "locks" / f"{session_id}.registry"
        held = json.loads(registry.read_text())
        assert len(held) == len(
            set(held)
        ), "Registry must not contain duplicate lock paths"

    @pytest.mark.parametrize(
        "tool_name", ["Write", "Edit", "MultiEdit", "NotebookEdit"]
    )
    def test_all_locking_tools_acquire_lock(self, tool_name, monkeypatch, tmp_path):
        """Every tool in LOCKING_TOOLS must trigger the full lock path (not the early-exit path)."""
        # NotebookEdit uses a different key name for its target path
        input_key = "notebook_path" if tool_name == "NotebookEdit" else "file_path"
        code, _ = self._run_main(
            {"tool_name": tool_name, "tool_input": {input_key: f"/tmp/{tool_name}.py"}},
            monkeypatch,
            tmp_path,
        )
        assert code == 0


# ---------------------------------------------------------------------------
# main() — timeout path
# ---------------------------------------------------------------------------


class TestMainTimeout:
    """Tests for the timeout branch: when another session holds the lock and the
    wait exceeds LOCK_TIMEOUT, main() must exit 2 and write a diagnostic to stderr."""

    def test_timeout_exits_2(self, monkeypatch, tmp_path, capsys):
        """Simulated lock contention must produce exit code 2 and a TIMEOUT message on stderr."""
        monkeypatch.setattr(fl, "LOCK_DIR", tmp_path / "locks")

        import io

        stdin_data = {
            "session_id": "sess-timeout",
            "tool_name": "Write",
            "tool_input": {"file_path": "/x.py"},
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(stdin_data)))

        # Patch acquire() to always raise the module's own Timeout
        with patch.object(fl, "acquire", side_effect=fl.Timeout("/fake.lock")):
            with pytest.raises(SystemExit) as exc_info:
                fl.main()

        assert exc_info.value.code == 2

        # The error message must identify the blocked file so the user knows what to do
        captured = capsys.readouterr()
        assert "TIMEOUT" in captured.err
        assert "/x.py" in captured.err
