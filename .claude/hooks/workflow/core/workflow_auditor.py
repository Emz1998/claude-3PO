#!/usr/bin/env python3
"""Workflow invariant auditor for detecting guard failures and state corruption.

Runs invariant checks at state mutation points and logs violations,
decisions, and warnings for post-hoc audit. The auditor never breaks
the workflow — all write errors are silently caught.
"""

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = "violations.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB


@dataclass
class Violation:
    """A detected invariant violation or warning."""

    severity: Literal["VIOLATION", "WARN"]
    check: str
    message: str


class WorkflowAuditor:
    """Audits workflow state for invariant violations and logs guard decisions."""

    def __init__(self, log_dir: Path = LOG_DIR):
        self._log_dir = log_dir
        self._log_path = log_dir / LOG_FILE

    # =========================================================================
    # Logging
    # =========================================================================

    def _ensure_log_dir(self) -> bool:
        """Create log directory if missing. Returns False on failure."""
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False

    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds MAX_LOG_SIZE."""
        try:
            if self._log_path.exists() and self._log_path.stat().st_size > MAX_LOG_SIZE:
                backup = self._log_path.with_suffix(".log.1")
                if backup.exists():
                    backup.unlink()
                self._log_path.rename(backup)
        except OSError:
            pass

    def _write_log(self, line: str) -> None:
        """Append a line to the log file. Silent on errors."""
        try:
            if not self._ensure_log_dir():
                return
            self._rotate_if_needed()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self._log_path, "a") as f:
                f.write(f"[{timestamp}] {line}\n")
        except OSError:
            pass

    def _log_violations(self, violations: list[Violation]) -> None:
        """Write violations to the log file."""
        for v in violations:
            self._write_log(f"[{v.severity}] [{v.check}] {v.message}")

    # =========================================================================
    # Invariant checks
    # =========================================================================

    def check_strict_order_compliance(
        self, deliverables: list[dict[str, Any]]
    ) -> list[Violation]:
        """Verify completed deliverables respect strict_order.

        For each completed deliverable with strict_order N, all deliverables
        with strict_order < N must also be complete.
        """
        violations: list[Violation] = []
        completed_orders: set[int] = set()
        pending_orders: set[int] = set()

        for d in deliverables:
            order = d.get("strict_order")
            if order is None:
                continue
            if d.get("completed", False):
                completed_orders.add(order)
            else:
                pending_orders.add(order)

        for completed in completed_orders:
            for pending in pending_orders:
                if pending < completed:
                    # Find the offending deliverable for context
                    for d in deliverables:
                        if (
                            d.get("strict_order") == completed
                            and d.get("completed", False)
                        ):
                            pattern = d.get("pattern", d.get("value", "?"))
                            action = d.get("action", "?")
                            violations.append(Violation(
                                severity="VIOLATION",
                                check="STRICT_ORDER",
                                message=(
                                    f"Level {completed} deliverable complete "
                                    f"while level {pending} still pending: "
                                    f"{action} {pattern}"
                                ),
                            ))
                            break
                    break  # One violation per completed/pending pair is enough

        self._log_violations(violations)
        return violations

    def check_phase_validity(self, phase: str) -> list[Violation]:
        """Verify phase exists in any known strategy's phase list."""
        violations: list[Violation] = []
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config.unified_loader import load_unified_config, is_bypass_phase  # type: ignore

            config = load_unified_config(validate=False)
            all_phases: set[str] = set()
            for phase_list in config.phases.values():
                if isinstance(phase_list, list):
                    all_phases.update(phase_list)

            if phase and phase not in all_phases:
                violations.append(Violation(
                    severity="VIOLATION",
                    check="PHASE_INVALID",
                    message=f"Phase '{phase}' not in any known phase list",
                ))
        except Exception:
            pass  # Config unavailable — skip check

        self._log_violations(violations)
        return violations

    def check_empty_deliverables(
        self, phase: str, deliverables: list[dict[str, Any]]
    ) -> list[Violation]:
        """Warn if a known phase has zero deliverables."""
        violations: list[Violation] = []

        # Skip check for bypass phases (e.g., troubleshoot)
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config.unified_loader import is_bypass_phase  # type: ignore

            if is_bypass_phase(phase):
                return violations
        except Exception:
            pass  # Config unavailable — skip bypass check

        if not deliverables:
            # Only warn if phase is valid (invalid phase already caught)
            phase_violations = self.check_phase_validity(phase)
            if not phase_violations and phase:
                violations.append(Violation(
                    severity="VIOLATION",
                    check="EMPTY_DELIVERABLES",
                    message=(
                        f"Phase '{phase}' initialized with 0 deliverables "
                        f"— config may be missing this phase"
                    ),
                ))
        self._log_violations(violations)
        return violations

    def check_state_integrity(self, state: dict[str, Any]) -> list[Violation]:
        """Verify required keys exist with correct types in state."""
        violations: list[Violation] = []
        expected: dict[str, type] = {
            "workflow_active": bool,
            "current_phase": str,
            "deliverables": list,
        }

        for key, expected_type in expected.items():
            if key not in state:
                violations.append(Violation(
                    severity="VIOLATION",
                    check="STATE_INTEGRITY",
                    message=f"State missing required key '{key}'",
                ))
            elif not isinstance(state[key], expected_type):
                actual = type(state[key]).__name__
                violations.append(Violation(
                    severity="VIOLATION",
                    check="STATE_INTEGRITY",
                    message=(
                        f"State key '{key}' has wrong type: "
                        f"expected {expected_type.__name__}, got {actual}"
                    ),
                ))

        self._log_violations(violations)
        return violations

    def check_state_corruption(
        self, state: dict[str, Any], was_fallback: bool
    ) -> list[Violation]:
        """Detect if state loaded as empty dict due to JSON corruption."""
        violations: list[Violation] = []
        if was_fallback:
            violations.append(Violation(
                severity="VIOLATION",
                check="STATE_CORRUPT",
                message="State loaded as empty dict (JSON corruption or read error)",
            ))
        self._log_violations(violations)
        return violations

    def check_phase_deliverable_match(
        self, phase: str, deliverables: list[dict[str, Any]]
    ) -> list[Violation]:
        """Verify deliverable count matches config for the phase."""
        violations: list[Violation] = []

        # Skip check for bypass phases (e.g., troubleshoot)
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config.unified_loader import is_bypass_phase  # type: ignore

            if is_bypass_phase(phase):
                return violations
        except Exception:
            pass  # Config unavailable — skip bypass check

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config.unified_loader import get_phase_deliverables_typed  # type: ignore

            expected_deliverables = get_phase_deliverables_typed(phase)
            expected_count = 0
            for action in ["read", "write", "edit"]:
                expected_count += len(getattr(expected_deliverables, action, []))
            expected_count += len(expected_deliverables.bash)
            expected_count += len(expected_deliverables.skill)

            actual_count = len(deliverables)

            if expected_count > 0 and actual_count != expected_count:
                violations.append(Violation(
                    severity="VIOLATION",
                    check="PHASE_MISMATCH",
                    message=(
                        f"Phase '{phase}' expects {expected_count} deliverables "
                        f"but state has {actual_count}"
                    ),
                ))
        except Exception:
            pass  # Config unavailable — skip check

        self._log_violations(violations)
        return violations

    # =========================================================================
    # Decision logging
    # =========================================================================

    def log_decision(self, guard: str, outcome: str, context: str) -> None:
        """Log a guard decision for audit trail."""
        self._write_log(f"[DECISION] [{guard}] {outcome} {context}")

    def log_warn(self, check: str, message: str) -> None:
        """Log a non-invariant warning."""
        self._write_log(f"[WARN] [{check}] {message}")


# =========================================================================
# Singleton
# =========================================================================

_auditor: WorkflowAuditor | None = None


def get_auditor(log_dir: Path | None = None) -> WorkflowAuditor:
    """Get the singleton WorkflowAuditor instance."""
    global _auditor
    if _auditor is None:
        _auditor = WorkflowAuditor(log_dir=log_dir or LOG_DIR)
    return _auditor
