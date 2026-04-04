"""Tests for auto_commit.py — async auto-commit hook."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.auto_commit import (
    get_dirty_files,
    claim_files,
    generate_commit_message,
    commit_files,
    load_ledger,
    save_ledger,
    cleanup_old_batches,
    get_story_context,
    EXCLUDE_PATTERNS,
)
from workflow.config import COMMIT_BATCH_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def init_git_repo(tmp_path: Path) -> Path:
    """Initialize a git repo in tmp_path and return it."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    # Create initial commit so HEAD exists
    (tmp_path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial commit"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    return tmp_path


def make_ledger(batches: list[dict]) -> dict:
    return {"batches": batches}


def make_batch(
    batch_id: str = "batch-1",
    files: list[str] | None = None,
    status: str = "pending",
    created_at: str | None = None,
    task_id: str = "task-1",
    task_subject: str = "Test task",
    commit_message: str | None = None,
) -> dict:
    batch = {
        "batch_id": batch_id,
        "task_id": task_id,
        "task_subject": task_subject,
        "files": files or [],
        "status": status,
        "created_at": created_at or datetime.now().isoformat(),
    }
    if commit_message:
        batch["commit_message"] = commit_message
    return batch


# ---------------------------------------------------------------------------
# TestGetDirtyFiles
# ---------------------------------------------------------------------------


class TestGetDirtyFiles:
    def test_returns_modified_files(self, tmp_path):
        repo = init_git_repo(tmp_path)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("print('hello')")
        (repo / "src" / "utils.py").write_text("x = 1")
        files = get_dirty_files(repo)
        assert "src/app.py" in files
        assert "src/utils.py" in files

    def test_excludes_state_json(self, tmp_path):
        repo = init_git_repo(tmp_path)
        (repo / "state.json").write_text("{}")
        files = get_dirty_files(repo)
        assert "state.json" not in files

    def test_excludes_pyc_files(self, tmp_path):
        repo = init_git_repo(tmp_path)
        (repo / "module.pyc").write_text("bytecode")
        files = get_dirty_files(repo)
        assert "module.pyc" not in files

    def test_excludes_pycache_dirs(self, tmp_path):
        repo = init_git_repo(tmp_path)
        cache_dir = repo / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "mod.cpython-312.pyc").write_text("bytecode")
        files = get_dirty_files(repo)
        assert not any("__pycache__" in f for f in files)

    def test_returns_empty_when_clean(self, tmp_path):
        repo = init_git_repo(tmp_path)
        files = get_dirty_files(repo)
        assert files == []


# ---------------------------------------------------------------------------
# TestClaimFiles
# ---------------------------------------------------------------------------


class TestClaimFiles:
    def test_claims_all_files_when_no_pending_batches(self):
        ledger = make_ledger([])
        dirty = ["src/a.py", "src/b.py"]
        claimed = claim_files(dirty, ledger)
        assert set(claimed) == {"src/a.py", "src/b.py"}

    def test_excludes_files_from_pending_batches(self):
        ledger = make_ledger([
            make_batch(batch_id="b1", files=["src/a.py"], status="pending"),
        ])
        dirty = ["src/a.py", "src/b.py"]
        claimed = claim_files(dirty, ledger)
        assert claimed == ["src/b.py"]

    def test_returns_empty_when_all_files_claimed(self):
        ledger = make_ledger([
            make_batch(batch_id="b1", files=["src/a.py", "src/b.py"], status="pending"),
        ])
        dirty = ["src/a.py", "src/b.py"]
        claimed = claim_files(dirty, ledger)
        assert claimed == []

    def test_reclaims_stale_pending_batches(self):
        stale_time = (datetime.now() - timedelta(minutes=15)).isoformat()
        ledger = make_ledger([
            make_batch(batch_id="b1", files=["src/a.py"], status="pending", created_at=stale_time),
        ])
        dirty = ["src/a.py", "src/b.py"]
        claimed = claim_files(dirty, ledger)
        # Stale batch files should be reclaimed
        assert set(claimed) == {"src/a.py", "src/b.py"}


# ---------------------------------------------------------------------------
# TestGenerateCommitMessage
# ---------------------------------------------------------------------------


class TestGenerateCommitMessage:
    @patch("workflow.auto_commit.subprocess.run")
    def test_returns_claude_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="feat: add user authentication\n",
            stderr="",
        )
        msg = generate_commit_message(
            files=["src/auth.py"],
            task_subject="Implement auth",
            task_description="Add JWT auth",
            project_dir=Path("/fake"),
        )
        assert msg == "feat: add user authentication"

    @patch("workflow.auto_commit.subprocess.run")
    def test_fallback_on_claude_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error",
        )
        msg = generate_commit_message(
            files=["src/auth.py"],
            task_subject="Implement auth",
            task_description="",
            project_dir=Path("/fake"),
        )
        assert msg == "chore: auto-commit after task (Implement auth)"

    @patch("workflow.auto_commit.subprocess.run")
    def test_fallback_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=120)
        msg = generate_commit_message(
            files=["src/auth.py"],
            task_subject="Implement auth",
            task_description="",
            project_dir=Path("/fake"),
        )
        assert msg == "chore: auto-commit after task (Implement auth)"


# ---------------------------------------------------------------------------
# TestStoryContext
# ---------------------------------------------------------------------------


class TestStoryContext:
    def test_loads_story_id_and_tasks(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({
            "story_id": "SK-001",
            "tasks": [
                {"id": "T-017", "subject": "Feature importance analysis", "status": "completed", "subtasks": []},
                {"id": "T-018", "subject": "Feature recommendations", "status": "completed", "subtasks": []},
            ],
        }))
        ctx = get_story_context(state_path)
        assert ctx["story_id"] == "SK-001"
        assert len(ctx["parent_tasks"]) == 2
        assert ctx["parent_tasks"][0]["id"] == "T-017"

    def test_returns_empty_when_no_state(self, tmp_path):
        state_path = tmp_path / "nonexistent.json"
        ctx = get_story_context(state_path)
        assert ctx == {}

    def test_returns_empty_when_no_story_id(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"workflow_active": True}))
        ctx = get_story_context(state_path)
        assert "story_id" not in ctx

    @patch("workflow.auto_commit.subprocess.run")
    def test_prompt_includes_story_context(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="feat(SK-001): add auth\n", stderr=""
        )
        story_ctx = {
            "story_id": "SK-001",
            "parent_tasks": [{"id": "T-017", "subject": "Feature analysis"}],
        }
        msg = generate_commit_message(
            files=["src/auth.py"],
            task_subject="Implement auth",
            task_description="Add JWT",
            project_dir=Path("/fake"),
            story_context=story_ctx,
        )
        assert msg == "feat(SK-001): add auth"
        # Verify the prompt sent to claude includes story context
        call_args = mock_run.call_args
        prompt_arg = call_args[0][0][2]  # claude -p <prompt>
        assert "SK-001" in prompt_arg
        assert "T-017" in prompt_arg
        assert "Feature analysis" in prompt_arg


# ---------------------------------------------------------------------------
# TestCommitFiles
# ---------------------------------------------------------------------------


class TestCommitFiles:
    def test_stages_and_commits(self, tmp_path):
        repo = init_git_repo(tmp_path)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("print('hello')")
        result = commit_files(
            files=["src/app.py"],
            message="feat: add app",
            project_dir=repo,
        )
        assert result is True
        # Verify commit exists
        log_out = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "feat: add app" in log_out.stdout

    def test_handles_commit_failure(self, tmp_path):
        repo = init_git_repo(tmp_path)
        # Try to commit a file that doesn't exist
        result = commit_files(
            files=["nonexistent.py"],
            message="feat: ghost file",
            project_dir=repo,
        )
        assert result is False


# ---------------------------------------------------------------------------
# TestBatchLedger
# ---------------------------------------------------------------------------


class TestBatchLedger:
    def test_saves_batch_with_pending_status(self, tmp_path):
        ledger_path = tmp_path / "commit_batch.json"
        ledger_path.write_text(json.dumps({"batches": []}))
        ledger = load_ledger(ledger_path)
        batch = make_batch(batch_id="b1", files=["a.py"], status="pending")
        ledger["batches"].append(batch)
        save_ledger(ledger, ledger_path)

        reloaded = load_ledger(ledger_path)
        assert len(reloaded["batches"]) == 1
        assert reloaded["batches"][0]["status"] == "pending"

    def test_updates_batch_to_committed(self, tmp_path):
        ledger_path = tmp_path / "commit_batch.json"
        batch = make_batch(batch_id="b1", files=["a.py"], status="pending")
        ledger = make_ledger([batch])
        save_ledger(ledger, ledger_path)

        loaded = load_ledger(ledger_path)
        loaded["batches"][0]["status"] = "committed"
        loaded["batches"][0]["commit_message"] = "feat: test"
        save_ledger(loaded, ledger_path)

        reloaded = load_ledger(ledger_path)
        assert reloaded["batches"][0]["status"] == "committed"
        assert reloaded["batches"][0]["commit_message"] == "feat: test"

    def test_cleans_up_old_committed_batches(self):
        batches = [
            make_batch(batch_id=f"b{i}", status="committed")
            for i in range(15)
        ]
        ledger = make_ledger(batches)
        cleaned = cleanup_old_batches(ledger, keep=10)
        assert len(cleaned["batches"]) == 10


# ---------------------------------------------------------------------------
# TestEndToEnd
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_flow_with_dirty_files(self, tmp_path):
        """Full flow: dirty files -> claim -> commit (mock claude only)."""
        repo = init_git_repo(tmp_path)

        # Create dirty files
        (repo / "feature.py").write_text("def feature(): pass")

        ledger_path = tmp_path / "commit_batch.json"
        ledger_path.write_text(json.dumps({"batches": []}))

        # Run the flow — only mock generate_commit_message
        dirty = get_dirty_files(repo)
        assert len(dirty) > 0

        ledger = load_ledger(ledger_path)
        claimed = claim_files(dirty, ledger)
        assert len(claimed) > 0

        with patch("workflow.auto_commit.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="feat: add feature\n", stderr=""
            )
            msg = generate_commit_message(
                files=claimed,
                task_subject="Add feature",
                task_description="",
                project_dir=repo,
            )
        assert msg == "feat: add feature"

        result = commit_files(files=claimed, message=msg, project_dir=repo)
        assert result is True

    def test_skip_when_no_dirty_files(self, tmp_path):
        repo = init_git_repo(tmp_path)
        dirty = get_dirty_files(repo)
        assert dirty == []

    def test_concurrent_batches_dont_overlap(self, tmp_path):
        """Two batches with overlapping dirty files claim distinct sets."""
        ledger = make_ledger([])

        # Batch 1 claims A, B, C
        dirty1 = ["a.py", "b.py", "c.py"]
        claimed1 = claim_files(dirty1, ledger)
        assert set(claimed1) == {"a.py", "b.py", "c.py"}

        # Record batch 1 as pending
        batch1 = make_batch(batch_id="b1", files=claimed1, status="pending")
        ledger["batches"].append(batch1)

        # Batch 2 sees A, B, C, D, E — should only claim D, E
        dirty2 = ["a.py", "b.py", "c.py", "d.py", "e.py"]
        claimed2 = claim_files(dirty2, ledger)
        assert set(claimed2) == {"d.py", "e.py"}
