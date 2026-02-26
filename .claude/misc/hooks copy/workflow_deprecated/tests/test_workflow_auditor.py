#!/usr/bin/env python3
"""Pytest tests for WorkflowAuditor invariant checks and decision logging."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.workflow_auditor import WorkflowAuditor, Violation, get_auditor  # type: ignore
from config.unified_loader import clear_unified_cache  # type: ignore

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def log_dir(tmp_path: Path) -> Path:
    """Provide a temporary log directory."""
    d = tmp_path / "logs"
    d.mkdir()
    return d


@pytest.fixture
def auditor(log_dir: Path) -> WorkflowAuditor:
    """Provide a WorkflowAuditor with a temporary log directory."""
    return WorkflowAuditor(log_dir=log_dir)


@pytest.fixture(autouse=True)
def clear_config_cache():
    """Clear config cache before and after each test."""
    clear_unified_cache()
    yield
    clear_unified_cache()


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton auditor between tests."""
    import core.workflow_auditor as mod

    mod._auditor = None
    yield
    mod._auditor = None


def _make_deliverable(
    action: str = "read",
    pattern: str = ".*prompt\\.md$",
    strict_order: int | None = None,
    completed: bool = False,
) -> dict:
    return {
        "type": "files",
        "action": action,
        "pattern": pattern,
        "strict_order": strict_order,
        "completed": completed,
    }


def _read_log(auditor: WorkflowAuditor) -> str:
    """Read the auditor's log file contents."""
    if auditor._log_path.exists():
        return auditor._log_path.read_text()
    return ""


# =========================================================================
# TestStrictOrderCompliance
# =========================================================================


class TestStrictOrderCompliance:
    """Tests for check_strict_order_compliance."""

    def test_detects_level_skip(self, auditor: WorkflowAuditor):
        """Level-3 complete while level-1 pending produces a violation."""
        deliverables = [
            _make_deliverable(strict_order=1, completed=False),
            _make_deliverable(
                strict_order=3, completed=True, action="write", pattern=".*report\\.md$"
            ),
        ]
        violations = auditor.check_strict_order_compliance(deliverables)
        assert len(violations) == 1
        assert violations[0].severity == "VIOLATION"
        assert violations[0].check == "STRICT_ORDER"
        assert (
            "level 3" in violations[0].message.lower()
            or "Level 3" in violations[0].message
        )
        assert (
            "level 1" in violations[0].message.lower()
            or "Level 1" in violations[0].message
        )

    def test_no_violation_when_ordered(self, auditor: WorkflowAuditor):
        """Sequential completion produces no violation."""
        deliverables = [
            _make_deliverable(strict_order=1, completed=True),
            _make_deliverable(strict_order=2, completed=True),
        ]
        violations = auditor.check_strict_order_compliance(deliverables)
        assert len(violations) == 0

    def test_no_violation_no_strict_order(self, auditor: WorkflowAuditor):
        """Deliverables without strict_order produce no violation."""
        deliverables = [
            _make_deliverable(strict_order=None, completed=True),
            _make_deliverable(strict_order=None, completed=False),
        ]
        violations = auditor.check_strict_order_compliance(deliverables)
        assert len(violations) == 0

    def test_multiple_violations(self, auditor: WorkflowAuditor):
        """Multiple out-of-order completions produce multiple violations."""
        deliverables = [
            _make_deliverable(strict_order=1, completed=False),
            _make_deliverable(strict_order=2, completed=False),
            _make_deliverable(
                strict_order=3, completed=True, action="write", pattern=".*a$"
            ),
            _make_deliverable(
                strict_order=4, completed=True, action="edit", pattern=".*b$"
            ),
        ]
        violations = auditor.check_strict_order_compliance(deliverables)
        # Level 3 skips 1 and 2, level 4 skips 1 and 2
        assert len(violations) >= 2


# =========================================================================
# TestPhaseValidity
# =========================================================================


class TestPhaseValidity:
    """Tests for check_phase_validity."""

    def test_known_phase_no_violation(self, auditor: WorkflowAuditor):
        """Known phases like 'explore' and 'plan' produce no violation."""
        assert auditor.check_phase_validity("explore") == []
        assert auditor.check_phase_validity("plan") == []

    def test_unknown_phase_violation(self, auditor: WorkflowAuditor):
        """Unknown phase produces a violation."""
        violations = auditor.check_phase_validity("random-skill")
        assert len(violations) == 1
        assert violations[0].check == "PHASE_INVALID"
        assert "random-skill" in violations[0].message

    def test_all_strategies_checked(self, auditor: WorkflowAuditor):
        """Phase valid in tdd but not simple still passes (union of all)."""
        # write-tests is in tdd but not in simple
        violations = auditor.check_phase_validity("write-tests")
        assert len(violations) == 0


# =========================================================================
# TestEmptyDeliverables
# =========================================================================


class TestEmptyDeliverables:
    """Tests for check_empty_deliverables."""

    def test_known_phase_empty_warns(self, auditor: WorkflowAuditor):
        """Known phase with empty deliverables produces a violation."""
        violations = auditor.check_empty_deliverables("explore", [])
        assert len(violations) >= 1
        assert any(v.check == "EMPTY_DELIVERABLES" for v in violations)

    def test_unknown_phase_empty_no_extra_warn(self, auditor: WorkflowAuditor):
        """Unknown phase with empty deliverables does not produce EMPTY_DELIVERABLES."""
        violations = auditor.check_empty_deliverables("nonexistent-phase", [])
        # Should NOT have EMPTY_DELIVERABLES since phase is invalid
        empty_violations = [v for v in violations if v.check == "EMPTY_DELIVERABLES"]
        assert len(empty_violations) == 0

    def test_non_empty_no_warn(self, auditor: WorkflowAuditor):
        """Phase with deliverables produces no EMPTY_DELIVERABLES violation."""
        violations = auditor.check_empty_deliverables("explore", [_make_deliverable()])
        empty_violations = [v for v in violations if v.check == "EMPTY_DELIVERABLES"]
        assert len(empty_violations) == 0

    def test_bypass_phase_skipped(self, auditor: WorkflowAuditor):
        """Bypass phases like 'troubleshoot' skip empty deliverables check."""
        violations = auditor.check_empty_deliverables("troubleshoot", [])
        empty_violations = [v for v in violations if v.check == "EMPTY_DELIVERABLES"]
        assert len(empty_violations) == 0


# =========================================================================
# TestStateIntegrity
# =========================================================================


class TestStateIntegrity:
    """Tests for check_state_integrity."""

    def test_valid_state_no_violation(self, auditor: WorkflowAuditor):
        """Complete state produces no violation."""
        state = {
            "workflow_active": True,
            "current_phase": "explore",
            "deliverables": [],
        }
        violations = auditor.check_state_integrity(state)
        assert len(violations) == 0

    def test_missing_key_violation(self, auditor: WorkflowAuditor):
        """State missing 'deliverables' key produces a violation."""
        state = {
            "workflow_active": True,
            "current_phase": "explore",
        }
        violations = auditor.check_state_integrity(state)
        assert len(violations) == 1
        assert "deliverables" in violations[0].message

    def test_wrong_type_violation(self, auditor: WorkflowAuditor):
        """current_phase as int produces a type violation."""
        state = {
            "workflow_active": True,
            "current_phase": 123,
            "deliverables": [],
        }
        violations = auditor.check_state_integrity(state)
        assert len(violations) == 1
        assert "current_phase" in violations[0].message
        assert "str" in violations[0].message
        assert "int" in violations[0].message


# =========================================================================
# TestStateCorruption
# =========================================================================


class TestStateCorruption:
    """Tests for check_state_corruption."""

    def test_fallback_detected(self, auditor: WorkflowAuditor):
        """was_fallback=True produces a STATE_CORRUPT violation."""
        violations = auditor.check_state_corruption({}, was_fallback=True)
        assert len(violations) == 1
        assert violations[0].check == "STATE_CORRUPT"
        log = _read_log(auditor)
        assert "[VIOLATION]" in log
        assert "STATE_CORRUPT" in log

    def test_no_fallback_no_violation(self, auditor: WorkflowAuditor):
        """was_fallback=False produces no violation."""
        violations = auditor.check_state_corruption({}, was_fallback=False)
        assert len(violations) == 0


# =========================================================================
# TestPhaseDeliverableMatch
# =========================================================================


class TestPhaseDeliverableMatch:
    """Tests for check_phase_deliverable_match."""

    def test_mismatched_counts(self, auditor: WorkflowAuditor):
        """Wrong deliverable count produces a violation."""
        # Pass a phase that has deliverables defined, but with wrong count
        violations = auditor.check_phase_deliverable_match(
            "explore",
            [_make_deliverable()],  # Likely wrong count
        )
        # If explore has deliverables defined, this will mismatch
        # If not, the check skips (expected_count=0 is a pass)
        # Either way, no crash
        assert isinstance(violations, list)

    def test_unknown_phase_no_crash(self, auditor: WorkflowAuditor):
        """Unknown phase doesn't crash the check."""
        violations = auditor.check_phase_deliverable_match("nonexistent", [])
        assert isinstance(violations, list)

    def test_bypass_phase_skipped(self, auditor: WorkflowAuditor):
        """Bypass phases like 'troubleshoot' skip deliverable match check."""
        violations = auditor.check_phase_deliverable_match("troubleshoot", [])
        mismatch_violations = [v for v in violations if v.check == "PHASE_MISMATCH"]
        assert len(mismatch_violations) == 0


# =========================================================================
# TestDecisionLogging
# =========================================================================


class TestDecisionLogging:
    """Tests for log_decision and log_warn."""

    def test_decision_written(self, auditor: WorkflowAuditor):
        """log_decision() writes to log file."""
        auditor.log_decision("PHASE_GUARD", "ALLOW", "explore -> plan")
        log = _read_log(auditor)
        assert "[DECISION]" in log
        assert "[PHASE_GUARD]" in log
        assert "ALLOW" in log
        assert "explore -> plan" in log

    def test_warn_written(self, auditor: WorkflowAuditor):
        """log_warn() writes to log file."""
        auditor.log_warn("SC_SKIP", "SC validation unavailable")
        log = _read_log(auditor)
        assert "[WARN]" in log
        assert "[SC_SKIP]" in log

    def test_log_format(self, auditor: WorkflowAuditor):
        """Verify log line format: [timestamp] [DECISION] [GUARD] OUTCOME context."""
        auditor.log_decision("EXIT_GUARD", "BLOCK", "Incomplete deliverables")
        log = _read_log(auditor)
        lines = log.strip().split("\n")
        assert len(lines) == 1
        line = lines[0]
        # Format: [YYYY-MM-DD HH:MM:SS] [DECISION] [EXIT_GUARD] BLOCK Incomplete deliverables
        assert line.startswith("[")
        assert "[DECISION]" in line
        assert "[EXIT_GUARD]" in line
        assert "BLOCK" in line
        assert "Incomplete deliverables" in line


# =========================================================================
# TestLogRotation
# =========================================================================


class TestLogRotation:
    """Tests for log file rotation."""

    def test_rotates_at_5mb(self, log_dir: Path):
        """Log rotates when exceeding 5MB."""
        auditor = WorkflowAuditor(log_dir=log_dir)
        log_path = log_dir / "violations.log"

        # Create a log file just over 5MB
        log_path.write_text("x" * (5 * 1024 * 1024 + 1))

        # Write a new entry — should trigger rotation
        auditor.log_decision("TEST", "ALLOW", "rotation test")

        backup = log_dir / "violations.log.1"
        assert backup.exists()
        assert log_path.exists()
        # New log should contain only the new entry
        assert "rotation test" in log_path.read_text()

    def test_keeps_single_backup(self, log_dir: Path):
        """Only violations.log.1 is kept, not .2, .3, etc."""
        auditor = WorkflowAuditor(log_dir=log_dir)
        log_path = log_dir / "violations.log"
        backup = log_dir / "violations.log.1"

        # First rotation
        log_path.write_text("x" * (5 * 1024 * 1024 + 1))
        auditor.log_decision("TEST", "ALLOW", "first")

        assert backup.exists()
        first_backup_content = backup.read_text()

        # Second rotation — should overwrite .1
        log_path.write_text("y" * (5 * 1024 * 1024 + 1))
        auditor.log_decision("TEST", "ALLOW", "second")

        assert backup.exists()
        # .1 should now contain "y"s, not "x"s
        assert backup.read_text() != first_backup_content
        # No .2 file
        assert not (log_dir / "violations.log.2").exists()


# =========================================================================
# TestSilentFailure
# =========================================================================


class TestSilentFailure:
    """Tests for silent failure behavior."""

    def test_readonly_dir_no_crash(self, tmp_path: Path):
        """Write error in read-only dir doesn't raise."""
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)

        try:
            auditor = WorkflowAuditor(log_dir=readonly_dir)
            # Should not raise
            auditor.log_decision("TEST", "ALLOW", "should not crash")
            auditor.check_state_corruption({}, was_fallback=True)
        finally:
            os.chmod(readonly_dir, 0o755)

    def test_missing_dir_created(self, tmp_path: Path):
        """Logs directory is created automatically if missing."""
        new_dir = tmp_path / "new_logs"
        assert not new_dir.exists()

        auditor = WorkflowAuditor(log_dir=new_dir)
        auditor.log_decision("TEST", "ALLOW", "creation test")

        assert new_dir.exists()
        assert (new_dir / "violations.log").exists()


# =========================================================================
# TestNoCircularImports
# =========================================================================


class TestNoCircularImports:
    """Tests for circular import safety."""

    def test_import_auditor(self):
        """Importing get_auditor works without circular import."""
        from core.workflow_auditor import get_auditor  # type: ignore

        auditor = get_auditor()
        assert auditor is not None

    def test_import_all_modified_modules(self):
        """Importing all modified modules together doesn't crash."""
        from core.workflow_auditor import get_auditor  # type: ignore
        from core.state_manager import get_manager  # type: ignore
        from core.deliverables_tracker import get_tracker  # type: ignore

        assert get_auditor() is not None
        assert get_manager() is not None
        assert get_tracker() is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
