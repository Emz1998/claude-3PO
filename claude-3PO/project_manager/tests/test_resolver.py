"""Tests for project_manager.resolver — pure rule engine, no I/O."""
from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from project_manager import resolver as rv


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _story(sid, status, tasks=None, blocked_by=None):
    # Minimal story dict sufficient for the resolver's rule checks.
    return {
        "id": sid,
        "status": status,
        "blocked_by": list(blocked_by or []),
        "tasks": list(tasks or []),
    }


def _task(tid, status):
    # Minimal task dict (no `tasks` children — tasks do not nest, and
    # tasks no longer carry blocking fields).
    return {
        "id": tid,
        "status": status,
    }


@pytest.fixture
def converged_backlog():
    # Stable backlog: every status already matches the rules → no changes.
    return {
        "stories": [
            _story("SK-001", "Done", tasks=[_task("T-001", "Done")]),
            _story("SK-002", "Backlog", blocked_by=["SK-003"]),  # SK-003 not Done
            _story("SK-003", "In progress", tasks=[_task("T-002", "In progress")]),
        ]
    }


# ---------------------------------------------------------------------------
# resolve() — top-level entry point
# ---------------------------------------------------------------------------


class TestResolveIdempotence:
    def test_returns_false_when_nothing_to_do(self, converged_backlog):
        before = deepcopy(converged_backlog)
        changed = rv.resolve(converged_backlog)
        assert changed is False
        assert converged_backlog == before

    def test_empty_backlog(self):
        backlog = {"stories": []}
        assert rv.resolve(backlog) is False

    def test_missing_stories_key(self):
        # Defensive: treat a stories-less dict as empty, don't crash.
        assert rv.resolve({}) is False


# ---------------------------------------------------------------------------
# Rule A: unblocked Backlog → Ready
# ---------------------------------------------------------------------------


class TestPromoteUnblocked:
    def test_story_with_no_blockers_promoted(self):
        backlog = {"stories": [_story("SK-001", "Backlog")]}
        assert rv.resolve(backlog) is True
        assert backlog["stories"][0]["status"] == "Ready"

    def test_story_with_done_blocker_promoted(self):
        backlog = {
            "stories": [
                _story("SK-001", "Done"),
                _story("SK-002", "Backlog", blocked_by=["SK-001"]),
            ]
        }
        assert rv.resolve(backlog) is True
        assert backlog["stories"][1]["status"] == "Ready"

    def test_story_with_pending_blocker_stays(self):
        backlog = {
            "stories": [
                _story("SK-001", "In progress"),
                _story("SK-002", "Backlog", blocked_by=["SK-001"]),
            ]
        }
        rv.resolve(backlog)
        assert backlog["stories"][1]["status"] == "Backlog"

    def test_task_in_backlog_promoted(self):
        backlog = {
            "stories": [
                _story("SK-001", "In progress", tasks=[_task("T-001", "Backlog")]),
            ]
        }
        rv.resolve(backlog)
        assert backlog["stories"][0]["tasks"][0]["status"] == "Ready"

    def test_task_promotes_without_blocked_by_field(self):
        # Tasks no longer carry `blocked_by` — the resolver must still
        # promote them when their parent has cleared the gate. Regression
        # guard for the model migration that stripped task blocking fields.
        backlog = {
            "stories": [
                _story(
                    "SK-001", "In progress",
                    tasks=[_task("T-001", "Backlog")],
                )
            ]
        }
        rv.resolve(backlog)
        assert backlog["stories"][0]["tasks"][0]["status"] == "Ready"

    def test_only_backlog_items_are_promoted(self):
        # `Ready` must not re-transition (Ready → Ready is a no-op but
        # Ready → In review would be an illegal auto-jump — see rule B test).
        backlog = {"stories": [_story("SK-001", "Ready")]}
        assert rv.resolve(backlog) is False


# ---------------------------------------------------------------------------
# Rule A — parent-story gate for tasks
# ---------------------------------------------------------------------------


class TestParentStoryGate:
    def test_task_gated_while_parent_backlog(self):
        # Parent story itself cannot leave Backlog (it has a pending blocker),
        # so its otherwise-unblocked child task must also stay Backlog.
        backlog = {
            "stories": [
                _story("SK-000", "In progress"),  # never becomes Done
                _story(
                    "SK-001", "Backlog", blocked_by=["SK-000"],
                    tasks=[_task("T-001", "Backlog")],
                ),
            ]
        }
        rv.resolve(backlog)
        assert backlog["stories"][1]["status"] == "Backlog"
        assert backlog["stories"][1]["tasks"][0]["status"] == "Backlog"

    def test_task_promotes_once_parent_ready(self):
        # Parent already out of Backlog → gate passes → task promotes.
        backlog = {
            "stories": [
                _story("SK-001", "Ready", tasks=[_task("T-001", "Backlog")]),
            ]
        }
        assert rv.resolve(backlog) is True
        assert backlog["stories"][0]["tasks"][0]["status"] == "Ready"

    def test_cascade_parent_ready_then_task_ready(self):
        # Single resolve() call: pass 1 promotes the parent (gate N/A for
        # stories), pass 2 sees parent == Ready and promotes the child.
        backlog = {
            "stories": [
                _story("SK-001", "Backlog", tasks=[_task("T-001", "Backlog")]),
            ]
        }
        assert rv.resolve(backlog) is True
        assert backlog["stories"][0]["status"] == "Ready"
        assert backlog["stories"][0]["tasks"][0]["status"] == "Ready"

    @pytest.mark.parametrize("parent_status", ["In progress", "In review", "Done"])
    def test_parent_in_progress_allows_task_promotion(self, parent_status):
        # Gate is "parent not Backlog" — any status past Backlog passes.
        backlog = {
            "stories": [
                _story("SK-001", parent_status, tasks=[_task("T-001", "Backlog")]),
            ]
        }
        rv.resolve(backlog)
        assert backlog["stories"][0]["tasks"][0]["status"] == "Ready"


# ---------------------------------------------------------------------------
# Rule B: In progress story with all tasks Done → In review
# ---------------------------------------------------------------------------


class TestPromoteStoryInReview:
    def test_all_tasks_done_promotes(self):
        backlog = {
            "stories": [
                _story(
                    "SK-001", "In progress",
                    tasks=[_task("T-001", "Done"), _task("T-002", "Done")],
                )
            ]
        }
        assert rv.resolve(backlog) is True
        assert backlog["stories"][0]["status"] == "In review"

    def test_one_task_not_done_stays(self):
        backlog = {
            "stories": [
                _story(
                    "SK-001", "In progress",
                    tasks=[_task("T-001", "Done"), _task("T-002", "In progress")],
                )
            ]
        }
        rv.resolve(backlog)
        assert backlog["stories"][0]["status"] == "In progress"

    def test_story_without_tasks_not_promoted(self):
        # No tasks → rule does not apply (avoids trivially promoting every
        # empty-shell story the moment it enters "In progress").
        backlog = {"stories": [_story("SK-001", "In progress")]}
        rv.resolve(backlog)
        assert backlog["stories"][0]["status"] == "In progress"

    def test_only_in_progress_stories_affected(self):
        # A "Ready" story whose tasks are all Done must NOT auto-jump to
        # "In review" — that violates VALID_TRANSITIONS.
        backlog = {
            "stories": [
                _story("SK-001", "Ready", tasks=[_task("T-001", "Done")]),
            ]
        }
        assert rv.resolve(backlog) is False
        assert backlog["stories"][0]["status"] == "Ready"


# ---------------------------------------------------------------------------
# Cascade — fixed-point iteration
# ---------------------------------------------------------------------------


class TestCascade:
    def test_done_story_unblocks_all_immediate_dependents(self):
        # Every Backlog item whose blockers are Done must promote in one
        # resolve() call, regardless of iteration order.
        backlog = {
            "stories": [
                _story("SK-001", "Done"),
                _story("SK-002", "Backlog", blocked_by=["SK-001"]),
                _story("SK-003", "Backlog", blocked_by=["SK-001"]),
            ]
        }
        assert rv.resolve(backlog) is True
        statuses = {s["id"]: s["status"] for s in backlog["stories"]}
        assert statuses["SK-002"] == "Ready"
        assert statuses["SK-003"] == "Ready"

    def test_rule_b_feeds_rule_a(self):
        # SK-001 flips In progress → In review because all its tasks are Done.
        # SK-002 is blocked by SK-001 — but SK-001 is not Done yet, so
        # SK-002 stays Backlog. This locks in that Rule B does NOT leak past
        # In review (no illegal In review → Done auto-transition).
        backlog = {
            "stories": [
                _story(
                    "SK-001", "In progress",
                    tasks=[_task("T-001", "Done")],
                ),
                _story("SK-002", "Backlog", blocked_by=["SK-001"]),
            ]
        }
        rv.resolve(backlog)
        statuses = {s["id"]: s["status"] for s in backlog["stories"]}
        assert statuses["SK-001"] == "In review"
        assert statuses["SK-002"] == "Backlog"


# ---------------------------------------------------------------------------
# VALID_TRANSITIONS respect
# ---------------------------------------------------------------------------


class TestValidTransitions:
    def test_resolver_never_produces_illegal_transition(self):
        # Try every starting status and verify the resolver only lands in a
        # state reachable per VALID_TRANSITIONS from the original.
        from project_manager.manager import VALID_TRANSITIONS

        for start in VALID_TRANSITIONS:
            backlog = {"stories": [_story("SK-001", start)]}
            rv.resolve(backlog)
            end = backlog["stories"][0]["status"]
            assert end == start or end in VALID_TRANSITIONS[start], (
                f"illegal auto-transition {start} -> {end}"
            )
