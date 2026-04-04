#!/usr/bin/env python3
"""
End-to-end tests for the file-lock hook trilogy:
  file_lock.py      (PreToolUse  → acquire)
  file_unlock.py    (PostToolUse → release)
  session_cleanup.py (SessionEnd  → release all held by a session)

Each test invokes the scripts as subprocesses via stdin/stdout/stderr exactly
the way Claude Code's hook runner does, then asserts on exit codes, stdout
payloads, lock files, and registry state on disk.
"""

import json
import os
import subprocess
import sys
import time
import multiprocessing
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths to the scripts under test
# ---------------------------------------------------------------------------

HOOKS_DIR = Path(__file__).parent.parent / "file_lock"
FILE_LOCK_SCRIPT    = HOOKS_DIR / "file_lock.py"
FILE_UNLOCK_SCRIPT  = HOOKS_DIR / "file_unlock.py"
SESSION_CLEANUP_SCRIPT = HOOKS_DIR / "session_cleanup.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_hook(script: Path, payload: dict, project_dir: Path, session_id: str = "sess-e2e") -> subprocess.CompletedProcess:
    """Invoke a hook script exactly as Claude Code would: JSON on stdin, env vars set."""
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),  # LOCK_DIR resolves to <project_dir>/.claude/locks
        "CLAUDE_SESSION_ID": session_id,
    }
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def lock_dir_for(tmp_path: Path) -> Path:
    """Returns the lock directory that the scripts will use given tmp_path as project dir."""
    return tmp_path / ".claude" / "locks"


# ---------------------------------------------------------------------------
# 1. Lock acquisition (file_lock.py)
# ---------------------------------------------------------------------------

class TestFileLockScript:
    def test_non_locking_tool_exits_0(self, tmp_path):
        result = run_hook(FILE_LOCK_SCRIPT, {
            "session_id": "s1",
            "tool_name": "Read",
            "tool_input": {"file_path": "/src/foo.py"},
        }, tmp_path)
        assert result.returncode == 0
        assert not (lock_dir_for(tmp_path)).exists()

    def test_successful_acquire_exits_0_with_context(self, tmp_path):
        result = run_hook(FILE_LOCK_SCRIPT, {
            "session_id": "s1",
            "tool_name": "Write",
            "tool_input": {"file_path": "/src/app.py"},
        }, tmp_path)
        assert result.returncode == 0
        out = json.loads(result.stdout)
        assert "additionalContext" in out
        assert "app.py" in out["additionalContext"]

    def test_lock_file_persists_after_subprocess_exit(self, tmp_path):
        """Lock file must survive subprocess exit so it blocks concurrent sessions
        between PreToolUse (acquire) and PostToolUse (release)."""
        session_id = "sess-meta"
        run_hook(FILE_LOCK_SCRIPT, {
            "session_id": session_id,
            "tool_name": "Edit",
            "tool_input": {"file_path": "/src/main.py"},
        }, tmp_path, session_id=session_id)

        lock_files = list(lock_dir_for(tmp_path).glob("*.lock"))
        assert len(lock_files) == 1

        meta = json.loads(lock_files[0].read_text())
        assert meta["session_id"] == session_id
        assert meta["file"] == "/src/main.py"
        assert "pid" in meta
        assert "acquired_at" in meta

    def test_registry_created_with_lock_entry(self, tmp_path):
        session_id = "sess-reg"
        run_hook(FILE_LOCK_SCRIPT, {
            "session_id": session_id,
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/out.txt"},
        }, tmp_path, session_id=session_id)

        registry = lock_dir_for(tmp_path) / f"{session_id}.registry"
        assert registry.exists()
        held = json.loads(registry.read_text())
        assert len(held) == 1
        assert held[0].endswith(".lock")

    @pytest.mark.parametrize("tool_name", ["Write", "Edit", "MultiEdit", "NotebookEdit"])
    def test_all_locking_tools_register_lock(self, tool_name, tmp_path):
        """Every locking tool must exit 0 and leave a registry entry."""
        session_id = "s1"
        key = "notebook_path" if tool_name == "NotebookEdit" else "file_path"
        result = run_hook(FILE_LOCK_SCRIPT, {
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_input": {key: f"/tmp/{tool_name}.py"},
        }, tmp_path, session_id=session_id)
        assert result.returncode == 0
        registry = lock_dir_for(tmp_path) / f"{session_id}.registry"
        assert registry.exists()


# ---------------------------------------------------------------------------
# 2. Lock release (file_unlock.py)
# ---------------------------------------------------------------------------

class TestFileUnlockScript:
    def _lock(self, tmp_path, session_id, file_path):
        run_hook(FILE_LOCK_SCRIPT, {
            "session_id": session_id,
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
        }, tmp_path, session_id=session_id)

    def test_release_clears_registry_entry(self, tmp_path):
        """file_unlock.py must remove the registry entry for the released file."""
        session_id = "sess-unlock"
        file_path = "/src/target.py"
        self._lock(tmp_path, session_id, file_path)

        registry = lock_dir_for(tmp_path) / f"{session_id}.registry"
        assert registry.exists()

        run_hook(FILE_UNLOCK_SCRIPT, {
            "session_id": session_id,
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
        }, tmp_path, session_id=session_id)

        assert not registry.exists()

    def test_release_clears_registry(self, tmp_path):
        session_id = "sess-reg-clear"
        file_path = "/src/reg.py"
        self._lock(tmp_path, session_id, file_path)

        run_hook(FILE_UNLOCK_SCRIPT, {
            "session_id": session_id,
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
        }, tmp_path, session_id=session_id)

        registry = lock_dir_for(tmp_path) / f"{session_id}.registry"
        assert not registry.exists()

    def test_unlock_non_locking_tool_exits_0(self, tmp_path):
        result = run_hook(FILE_UNLOCK_SCRIPT, {
            "session_id": "s1",
            "tool_name": "Read",
            "tool_input": {"file_path": "/foo.py"},
        }, tmp_path)
        assert result.returncode == 0

    def test_unlock_without_prior_lock_exits_0(self, tmp_path):
        """Unlocking a file that was never locked must be a no-op."""
        result = run_hook(FILE_UNLOCK_SCRIPT, {
            "session_id": "sess-noop",
            "tool_name": "Write",
            "tool_input": {"file_path": "/never/locked.py"},
        }, tmp_path)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 3. Full lock → work → unlock lifecycle
# ---------------------------------------------------------------------------

class TestLockUnlockLifecycle:
    def test_lock_then_unlock_then_reacquire(self, tmp_path):
        """After unlock, the same file can be locked again immediately."""
        session_id = "sess-lifecycle"
        payload_lock = {
            "session_id": session_id,
            "tool_name": "Write",
            "tool_input": {"file_path": "/src/lifecycle.py"},
        }
        payload_unlock = {
            "session_id": session_id,
            "tool_name": "Write",
            "tool_input": {"file_path": "/src/lifecycle.py"},
        }

        r1 = run_hook(FILE_LOCK_SCRIPT, payload_lock, tmp_path, session_id=session_id)
        assert r1.returncode == 0

        run_hook(FILE_UNLOCK_SCRIPT, payload_unlock, tmp_path, session_id=session_id)

        r2 = run_hook(FILE_LOCK_SCRIPT, payload_lock, tmp_path, session_id=session_id)
        assert r2.returncode == 0

    def test_two_files_independent_locks(self, tmp_path):
        """Locking file A must not block locking file B; both must appear in the registry."""
        session_id = "sess-two"
        for file_path in ["/src/a.py", "/src/b.py"]:
            r = run_hook(FILE_LOCK_SCRIPT, {
                "session_id": session_id,
                "tool_name": "Write",
                "tool_input": {"file_path": file_path},
            }, tmp_path, session_id=session_id)
            assert r.returncode == 0

        registry = lock_dir_for(tmp_path) / f"{session_id}.registry"
        held = json.loads(registry.read_text())
        assert len(held) == 2

    def test_registry_tracks_multiple_locks(self, tmp_path):
        session_id = "sess-multi"
        for file_path in ["/src/x.py", "/src/y.py", "/src/z.py"]:
            run_hook(FILE_LOCK_SCRIPT, {
                "session_id": session_id,
                "tool_name": "Write",
                "tool_input": {"file_path": file_path},
            }, tmp_path, session_id=session_id)

        registry = lock_dir_for(tmp_path) / f"{session_id}.registry"
        held = json.loads(registry.read_text())
        assert len(held) == 3


# ---------------------------------------------------------------------------
# 4. Session cleanup (session_cleanup.py)
# ---------------------------------------------------------------------------

class TestSessionCleanup:
    def test_cleanup_clears_registry(self, tmp_path):
        """SessionEnd hook must clear the registry for the session."""
        session_id = "sess-cleanup"
        for file_path in ["/a.py", "/b.py", "/c.py"]:
            run_hook(FILE_LOCK_SCRIPT, {
                "session_id": session_id,
                "tool_name": "Write",
                "tool_input": {"file_path": file_path},
            }, tmp_path, session_id=session_id)

        registry = lock_dir_for(tmp_path) / f"{session_id}.registry"
        assert registry.exists()
        assert len(json.loads(registry.read_text())) == 3

        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "CLAUDE_SESSION_ID": session_id,
        }
        result = subprocess.run(
            [sys.executable, str(SESSION_CLEANUP_SCRIPT)],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0
        assert not registry.exists()

    def test_cleanup_only_removes_own_session_registry(self, tmp_path):
        """Session A's cleanup must not touch session B's registry."""
        for session_id, file_path in [("sess-A", "/a.py"), ("sess-B", "/b.py")]:
            run_hook(FILE_LOCK_SCRIPT, {
                "session_id": session_id,
                "tool_name": "Write",
                "tool_input": {"file_path": file_path},
            }, tmp_path, session_id=session_id)

        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "CLAUDE_SESSION_ID": "sess-A"}
        subprocess.run([sys.executable, str(SESSION_CLEANUP_SCRIPT)], env=env, capture_output=True)

        assert not (lock_dir_for(tmp_path) / "sess-A.registry").exists()
        assert (lock_dir_for(tmp_path) / "sess-B.registry").exists()

    def test_cleanup_no_registry_is_noop(self, tmp_path):
        """Cleanup on a session that never held any locks must exit 0 cleanly."""
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "CLAUDE_SESSION_ID": "sess-ghost"}
        result = subprocess.run(
            [sys.executable, str(SESSION_CLEANUP_SCRIPT)],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 5. Cross-session contention (two sessions competing for the same file)
# ---------------------------------------------------------------------------

def _session_lock_subprocess(script, payload, tmp_path, session_id, result_path):
    """Worker: run file_lock.py as a subprocess and write the exit code to result_path."""
    r = run_hook(script, payload, tmp_path, session_id=session_id)
    Path(result_path).write_text(str(r.returncode))


class TestCrossSessionContention:
    def test_second_session_blocked_until_first_releases(self, tmp_path):
        """Session B must wait while session A holds the lock on the same file."""
        file_path = "/shared/model.py"
        lock_dir = lock_dir_for(tmp_path)
        lock_dir.mkdir(parents=True, exist_ok=True)

        # Manually pre-acquire the lock as session A (simulates A still editing)
        from filelock import SoftFileLock
        safe = file_path.replace("/", "_").strip("_")
        lock_path = lock_dir / f"{safe}.lock"
        lock_a = SoftFileLock(str(lock_path), timeout=10)
        lock_a.acquire()
        lock_path.write_text(json.dumps({
            "session_id": "sess-A",
            "pid": os.getpid(),
            "file": file_path,
            "acquired_at": time.time(),
        }))

        # Session B tries to acquire with a short timeout — must time out
        result_path = str(tmp_path / "sess_b_result.txt")
        payload = {
            "session_id": "sess-B",
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
        }
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "CLAUDE_SESSION_ID": "sess-B",
        }

        # Patch LOCK_TIMEOUT to 1s so the test doesn't wait 30s
        patched_script = tmp_path / "file_lock_short_timeout.py"
        original = FILE_LOCK_SCRIPT.read_text()
        patched_script.write_text(original.replace("LOCK_TIMEOUT = 30", "LOCK_TIMEOUT = 1"))

        result_b = subprocess.run(
            [sys.executable, str(patched_script)],
            input=json.dumps(payload),
            capture_output=True, text=True, env=env,
        )

        lock_a.release()

        assert result_b.returncode == 2, "Session B should have timed out (exit 2)"
        assert "TIMEOUT" in result_b.stderr
        assert file_path in result_b.stderr

    def test_second_session_acquires_after_first_unlocks(self, tmp_path):
        """Session B must succeed once session A explicitly releases via file_unlock.py."""
        session_a = "sess-A2"
        session_b = "sess-B2"
        file_path = "/shared/config.py"

        # Session A acquires
        r_a = run_hook(FILE_LOCK_SCRIPT, {
            "session_id": session_a,
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
        }, tmp_path, session_id=session_a)
        assert r_a.returncode == 0

        # Session A releases
        run_hook(FILE_UNLOCK_SCRIPT, {
            "session_id": session_a,
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
        }, tmp_path, session_id=session_a)

        # Session B should now acquire cleanly
        r_b = run_hook(FILE_LOCK_SCRIPT, {
            "session_id": session_b,
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
        }, tmp_path, session_id=session_b)
        assert r_b.returncode == 0
        out = json.loads(r_b.stdout)
        assert "additionalContext" in out
