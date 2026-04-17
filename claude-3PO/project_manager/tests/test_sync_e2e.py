"""Live end-to-end tests for project_manager.sync.Syncer.

These hit real GitHub and **destructively** wipe all issues in the configured
project before each run. They are gated behind the ``e2e`` pytest marker —
run with ``pytest -m e2e``.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from project_manager import Syncer
from project_manager import sync as sp

_E2E_ID_PREFIXES = ("SK-E2E-", "TS-E2E-", "T-E2E-")


def _cleanup_orphan_e2e_issues(repo: str) -> None:
    """Delete any [E2E]-prefixed issues that escaped project-scoped cleanup."""
    for issue in sp._fetch_all_issues(repo, "all"):
        title = issue.get("title", "")
        if any(pref in title for pref in _E2E_ID_PREFIXES):
            sp._delete_issue(repo, issue["number"])


def _gh_authenticated() -> bool:
    try:
        r = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, timeout=10
        )
        return r.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


_requires_gh = pytest.mark.skipif(
    not _gh_authenticated(),
    reason="requires `gh` CLI authenticated to GitHub",
)


# ---------------------------------------------------------------------------
# Sample backlog — titles prefixed with [E2E] for identifiability
# ---------------------------------------------------------------------------


_SAMPLE_BACKLOG: dict = {
    "project": "E2E Test",
    "goal": "End-to-end smoke test for Syncer",
    "dates": {"start": "2026-04-17", "end": "2026-04-24"},
    "totalPoints": 5,
    "stories": [
        {
            "id": "SK-E2E-001",
            "type": "Spike",
            "milestone": "e2e-v0.1",
            "labels": ["e2e"],
            "title": "[E2E] Research topic",
            "description": "E2E story A",
            "points": 3,
            "status": "In progress",
            "priority": "P0",
            "is_blocking": [],
            "blocked_by": [],
            "acceptance_criteria": ["criterion 1", "criterion 2"],
            "start_date": "2026-04-17",
            "target_date": "2026-04-18",
            "tasks": [
                {
                    "id": "T-E2E-001",
                    "type": "task",
                    "labels": ["e2e"],
                    "title": "[E2E] Task A1",
                    "description": "E2E task A1",
                    "status": "Ready",
                    "priority": "P1",
                    "complexity": "S",
                    "is_blocking": [],
                    "blocked_by": [],
                    "acceptance_criteria": [],
                },
                {
                    "id": "T-E2E-002",
                    "type": "task",
                    "labels": ["e2e"],
                    "title": "[E2E] Task A2 (blocked by A1)",
                    "description": "E2E task A2",
                    "status": "Backlog",
                    "priority": "P2",
                    "complexity": "M",
                    "is_blocking": [],
                    "blocked_by": ["T-E2E-001"],
                    "acceptance_criteria": [],
                },
            ],
        },
        {
            "id": "TS-E2E-001",
            "type": "Tech",
            "milestone": "e2e-v0.1",
            "labels": ["e2e"],
            "title": "[E2E] Infrastructure setup",
            "description": "E2E story B",
            "points": 2,
            "status": "Ready",
            "priority": "P1",
            "is_blocking": [],
            "blocked_by": ["SK-E2E-001"],
            "acceptance_criteria": [],
            "start_date": "",
            "target_date": "",
            "tasks": [
                {
                    "id": "T-E2E-003",
                    "type": "task",
                    "labels": ["e2e"],
                    "title": "[E2E] Task B1",
                    "description": "E2E task B1",
                    "status": "Backlog",
                    "priority": "P2",
                    "complexity": "S",
                    "is_blocking": [],
                    "blocked_by": [],
                    "acceptance_criteria": [],
                },
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_created_titles():
    """Reset the thread-dedup set between tests."""
    sp._created_titles.clear()
    yield
    sp._created_titles.clear()


@pytest.fixture
def backlog_path(tmp_path: Path) -> Path:
    p = tmp_path / "backlog.json"
    p.write_text(json.dumps(_SAMPLE_BACKLOG, indent=2), encoding="utf-8")
    return p


@pytest.fixture
def syncer(backlog_path: Path):
    """Yield a Syncer with the GitHub project pre-wiped + orphans cleared."""
    s = Syncer(backlog_path=backlog_path)
    s.run("delete-all")
    _cleanup_orphan_e2e_issues(s.repo)
    yield s
    s.run("delete-all")
    _cleanup_orphan_e2e_issues(s.repo)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _has_issue_numbers(backlog_data: dict) -> bool:
    for story in backlog_data.get("stories", []):
        if not story.get("issue_number"):
            return False
        for task in story.get("tasks", []):
            if not task.get("issue_number"):
                return False
    return True


def _no_issue_numbers(backlog_data: dict) -> bool:
    for story in backlog_data.get("stories", []):
        if "issue_number" in story:
            return False
        for task in story.get("tasks", []):
            if "issue_number" in task:
                return False
    return True


@pytest.mark.e2e
@_requires_gh
class TestSyncerE2E:
    def test_sync_creates_issues_and_writes_back(
        self, syncer: Syncer, backlog_path: Path
    ) -> None:
        assert syncer.run("sync") == 0
        data = json.loads(backlog_path.read_text(encoding="utf-8"))
        assert _has_issue_numbers(data), (
            f"Expected issue_numbers on every story and task; got: {data}"
        )
        # Verify items actually landed in the GitHub project (not just repo)
        project_issues = sp._project_issues(syncer.project, syncer.owner)
        assert len(project_issues) == 5, (
            f"Expected 5 project items after sync; found {len(project_issues)}: "
            f"{[iss['title'] for iss in project_issues]}"
        )

    def test_delete_all_clears_issue_numbers(
        self, syncer: Syncer, backlog_path: Path
    ) -> None:
        # Populate first
        syncer.run("sync")
        mid = json.loads(backlog_path.read_text(encoding="utf-8"))
        assert _has_issue_numbers(mid), "sync should have assigned issue_numbers"
        # Wipe and verify backlog cleared
        assert syncer.run("delete-all") == 0
        after = json.loads(backlog_path.read_text(encoding="utf-8"))
        assert _no_issue_numbers(after), (
            f"delete-all should strip issue_numbers; got: {after}"
        )

    def test_dry_run_does_not_write_back(
        self, syncer: Syncer, backlog_path: Path
    ) -> None:
        assert syncer.run("sync", dry_run=True) == 0
        data = json.loads(backlog_path.read_text(encoding="utf-8"))
        assert _no_issue_numbers(data), (
            f"dry-run must not write issue_numbers back to disk; got: {data}"
        )
