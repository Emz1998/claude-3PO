"""Tests for auto_commit.py — ledger, claiming, parsing, and batch lifecycle."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from utils.auto_commit import (
    load_ledger,
    save_ledger,
    cleanup_old_batches,
    _is_excluded,
    _resolve_rename,
    _parse_porcelain_line,
    _is_batch_stale,
    _collect_claimed_files,
    claim_files,
    _build_commit_prompt,
    _add_pending_batch,
    _update_batch_status,
    STALE_THRESHOLD_MINUTES,
)


# ── Exclude patterns ─────────────────────────────────────────────


class TestIsExcluded:
    def test_state_jsonl(self):
        assert _is_excluded("state.jsonl") is True

    def test_state_json(self):
        assert _is_excluded("state.json") is True

    def test_nested_state(self):
        assert _is_excluded("claudeguard/scripts/state.jsonl") is True

    def test_pyc(self):
        assert _is_excluded("utils/__pycache__/foo.cpython-312.pyc") is True

    def test_lock_file(self):
        assert _is_excluded("something.lock") is True

    def test_commit_batch(self):
        assert _is_excluded("commit_batch.json") is True

    def test_normal_py(self):
        assert _is_excluded("src/app.py") is False

    def test_normal_ts(self):
        assert _is_excluded("src/index.ts") is False


# ── Rename resolution ─────────────────────────────────────────────


class TestResolveRename:
    def test_rename(self):
        assert _resolve_rename("old.py -> new.py") == "new.py"

    def test_no_rename(self):
        assert _resolve_rename("app.py") == "app.py"


# ── Porcelain line parsing ────────────────────────────────────────


class TestParsePorcelainLine:
    def test_modified(self):
        assert _parse_porcelain_line(" M src/app.py") == "src/app.py"

    def test_added(self):
        assert _parse_porcelain_line("A  src/new.py") == "src/new.py"

    def test_untracked(self):
        assert _parse_porcelain_line("?? src/draft.py") == "src/draft.py"

    def test_renamed(self):
        assert _parse_porcelain_line("R  old.py -> new.py") == "new.py"

    def test_excluded(self):
        assert _parse_porcelain_line(" M state.jsonl") is None

    def test_empty_line(self):
        assert _parse_porcelain_line("") is None

    def test_short_line(self):
        assert _parse_porcelain_line("AB") is None


# ── Ledger I/O ────────────────────────────────────────────────────


class TestLedgerIO:
    def test_load_missing_file(self, tmp_path):
        result = load_ledger(tmp_path / "missing.json")
        assert result == {"batches": []}

    def test_load_empty_file(self, tmp_path):
        path = tmp_path / "ledger.json"
        path.write_text("")
        assert load_ledger(path) == {"batches": []}

    def test_load_invalid_json(self, tmp_path):
        path = tmp_path / "ledger.json"
        path.write_text("{not valid")
        assert load_ledger(path) == {"batches": []}

    def test_load_missing_batches_key(self, tmp_path):
        path = tmp_path / "ledger.json"
        path.write_text(json.dumps({"other": "data"}))
        result = load_ledger(path)
        assert result["batches"] == []

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "ledger.json"
        ledger = {"batches": [{"batch_id": "b1", "status": "pending", "files": ["a.py"]}]}
        save_ledger(ledger, path)
        loaded = load_ledger(path)
        assert loaded["batches"][0]["batch_id"] == "b1"


# ── Cleanup ───────────────────────────────────────────────────────


class TestCleanupOldBatches:
    def test_keeps_recent(self):
        batches = [{"batch_id": f"b{i}", "status": "committed"} for i in range(5)]
        ledger = cleanup_old_batches({"batches": batches}, keep=10)
        assert len(ledger["batches"]) == 5

    def test_trims_excess(self):
        batches = [{"batch_id": f"b{i}", "status": "committed"} for i in range(15)]
        ledger = cleanup_old_batches({"batches": batches}, keep=3)
        committed = [b for b in ledger["batches"] if b["status"] == "committed"]
        assert len(committed) == 3
        assert committed[0]["batch_id"] == "b12"

    def test_preserves_non_committed(self):
        batches = [
            {"batch_id": "pending1", "status": "pending"},
            {"batch_id": "c1", "status": "committed"},
            {"batch_id": "c2", "status": "committed"},
        ]
        ledger = cleanup_old_batches({"batches": batches}, keep=1)
        assert any(b["batch_id"] == "pending1" for b in ledger["batches"])
        committed = [b for b in ledger["batches"] if b["status"] == "committed"]
        assert len(committed) == 1


# ── Batch staleness ───────────────────────────────────────────────


class TestIsBatchStale:
    def test_fresh_batch(self):
        batch = {"created_at": datetime.now().isoformat()}
        cutoff = datetime.now() - timedelta(minutes=STALE_THRESHOLD_MINUTES)
        assert _is_batch_stale(batch, cutoff) is False

    def test_stale_batch(self):
        old = datetime.now() - timedelta(minutes=STALE_THRESHOLD_MINUTES + 5)
        batch = {"created_at": old.isoformat()}
        cutoff = datetime.now() - timedelta(minutes=STALE_THRESHOLD_MINUTES)
        assert _is_batch_stale(batch, cutoff) is True

    def test_missing_timestamp(self):
        cutoff = datetime.now() - timedelta(minutes=STALE_THRESHOLD_MINUTES)
        assert _is_batch_stale({}, cutoff) is True

    def test_invalid_timestamp(self):
        cutoff = datetime.now() - timedelta(minutes=STALE_THRESHOLD_MINUTES)
        assert _is_batch_stale({"created_at": "not-a-date"}, cutoff) is True


# ── Claiming ──────────────────────────────────────────────────────


class TestClaimFiles:
    def test_no_pending_batches(self):
        ledger = {"batches": []}
        assert claim_files(["a.py", "b.py"], ledger) == ["a.py", "b.py"]

    def test_excludes_already_claimed(self):
        ledger = {"batches": [{
            "status": "pending",
            "files": ["a.py"],
            "created_at": datetime.now().isoformat(),
        }]}
        assert claim_files(["a.py", "b.py"], ledger) == ["b.py"]

    def test_stale_batch_releases_files(self):
        old = datetime.now() - timedelta(minutes=STALE_THRESHOLD_MINUTES + 5)
        ledger = {"batches": [{
            "status": "pending",
            "files": ["a.py"],
            "created_at": old.isoformat(),
        }]}
        result = claim_files(["a.py", "b.py"], ledger)
        assert "a.py" in result
        assert ledger["batches"][0]["status"] == "failed"

    def test_committed_batches_ignored(self):
        ledger = {"batches": [{
            "status": "committed",
            "files": ["a.py"],
            "created_at": datetime.now().isoformat(),
        }]}
        assert claim_files(["a.py"], ledger) == ["a.py"]


# ── Add pending batch ─────────────────────────────────────────────


class TestAddPendingBatch:
    def test_appends_entry(self):
        ledger = {"batches": []}
        _add_pending_batch(ledger, "b1", "t1", "Fix bug", ["a.py"])
        assert len(ledger["batches"]) == 1
        entry = ledger["batches"][0]
        assert entry["batch_id"] == "b1"
        assert entry["task_id"] == "t1"
        assert entry["status"] == "pending"
        assert entry["files"] == ["a.py"]
        assert "created_at" in entry


# ── Update batch status ───────────────────────────────────────────


class TestUpdateBatchStatus:
    def test_marks_committed(self):
        ledger = {"batches": [{"batch_id": "b1", "status": "pending"}]}
        _update_batch_status(ledger, "b1", True, "feat: add login")
        assert ledger["batches"][0]["status"] == "committed"
        assert ledger["batches"][0]["commit_message"] == "feat: add login"

    def test_marks_failed(self):
        ledger = {"batches": [{"batch_id": "b1", "status": "pending"}]}
        _update_batch_status(ledger, "b1", False, "feat: add login")
        assert ledger["batches"][0]["status"] == "failed"
        assert "commit_message" not in ledger["batches"][0]

    def test_unknown_batch_noop(self):
        ledger = {"batches": [{"batch_id": "b1", "status": "pending"}]}
        _update_batch_status(ledger, "b999", True, "msg")
        assert ledger["batches"][0]["status"] == "pending"


# ── Commit prompt ─────────────────────────────────────────────────


class TestBuildCommitPrompt:
    def test_includes_files_and_task(self):
        prompt = _build_commit_prompt(["a.py", "b.py"], "Fix login", "OAuth was broken")
        assert "- a.py" in prompt
        assert "- b.py" in prompt
        assert "Fix login" in prompt
        assert "OAuth was broken" in prompt
        assert "conventional commit" in prompt
