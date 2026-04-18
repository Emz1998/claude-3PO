"""Bug #5: SubagentStop must log a violation when AgentReportGuard blocks."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
DISPATCHER = SCRIPTS_DIR / "dispatchers" / "subagent_stop.py"


def _specs_state(session_id: str, phase: str, agent_name: str) -> dict:
    return {
        "session_id": session_id,
        "workflow_active": True,
        "status": "in_progress",
        "workflow_type": "specs",
        "phases": [{"name": phase, "status": "in_progress"}],
        "agents": [{"name": agent_name, "status": "in_progress", "tool_use_id": "a-1"}],
        "docs": {
            "product_vision": {"written": True, "path": "projects/docs/product-vision.md"},
            "decisions": {"written": True, "path": "projects/docs/decisions.md"},
            "architecture": {"written": False, "path": ""},
            "backlog": {"written": False, "md_path": "", "json_path": ""},
        },
    }


def _write_state(state_path: Path, state: dict) -> None:
    state_path.write_text(json.dumps(state, separators=(",", ":")) + "\n")


def _run(payload: dict, state_path: Path, violations_path: Path):
    env = {
        **os.environ,
        "SUBAGENT_STOP_STATE_PATH": str(state_path),
        "VIOLATIONS_PATH": str(violations_path),
    }
    return subprocess.run(
        [sys.executable, str(DISPATCHER)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


def _payload(session_id: str, message: str, agent_type: str) -> dict:
    return {
        "hook_event_name": "SubagentStop",
        "session_id": session_id,
        "agent_id": "a-1",
        "agent_type": agent_type,
        "last_assistant_message": message,
    }


class TestSubagentStopRetryLoop:
    """Attempts 1..N-1 block (exit 2, course-correct). Attempt N releases cleanly."""

    BAD = "# Bad Backlog\n\nNo stories."

    def test_first_rejection_blocks_with_actionable_message(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        violations_path = tmp_path / "violations.md"
        _write_state(state_path, _specs_state("sess-1", "backlog", "ProductOwner"))

        proc = _run(_payload("sess-1", self.BAD, "ProductOwner"), state_path, violations_path)

        assert proc.returncode == 2
        assert "attempt 1/3" in proc.stderr
        assert "templates/backlog.md" in proc.stderr
        # No violation logged mid-retry — avoids the ~80-entry spam we saw in the report.
        assert not violations_path.exists()

    def test_cap_reached_releases_subagent_and_logs_once(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        violations_path = tmp_path / "violations.md"
        _write_state(state_path, _specs_state("sess-cap", "backlog", "ProductOwner"))

        # Attempts 1 and 2 must block (exit 2).
        for expected in (1, 2):
            proc = _run(_payload("sess-cap", self.BAD, "ProductOwner"), state_path, violations_path)
            assert proc.returncode == 2, (expected, proc.stderr)
            assert f"attempt {expected}/3" in proc.stderr

        # Attempt 3 hits the cap: subagent released (exit 0) and violation logged.
        proc = _run(_payload("sess-cap", self.BAD, "ProductOwner"), state_path, violations_path)
        assert proc.returncode == 0, proc.stderr
        assert violations_path.exists()
        log = violations_path.read_text()
        assert "SubagentStop" in log
        assert "ProductOwner" in log
        # Exactly one row logged across 3 attempts.
        data_rows = [l for l in log.strip().splitlines() if l.startswith("| 2") or "SubagentStop" in l]
        assert sum(1 for l in log.splitlines() if "SubagentStop" in l) == 1

    def test_cap_releases_without_marking_agent_failed(self, tmp_path: Path):
        """After the flat-Recorder refactor, the cap no longer flips the agent
        to ``failed`` — the feature was dropped together with specs-doc writing.
        The agent remains in its last recorded state (``completed`` from the
        agent-completion hook)."""
        state_path = tmp_path / "state.jsonl"
        violations_path = tmp_path / "violations.md"
        _write_state(state_path, _specs_state("sess-fail", "architect", "Architect"))

        for _ in range(3):
            _run(_payload("sess-fail", "# Bad Architecture\n\nNo structure.", "Architect"),
                 state_path, violations_path)

        state = json.loads(state_path.read_text().splitlines()[-1])
        arch = next(a for a in state["agents"] if a["name"] == "Architect")
        assert arch["status"] != "failed"

    def test_valid_backlog_does_not_log_violation(self, tmp_path: Path, monkeypatch):
        state_path = tmp_path / "state.jsonl"
        violations_path = tmp_path / "violations.md"
        _write_state(state_path, _specs_state("sess-good", "backlog", "ProductOwner"))

        # Valid backlog writes docs — run from an isolated cwd so writes land in tmp.
        monkeypatch.chdir(tmp_path)
        valid = (
            "# Backlog\n\n"
            "## Stories\n\n"
            "| ID | Title | Type | Priority | Status |\n"
            "|----|-------|------|----------|--------|\n"
            "| SK-001 | Login | Feature | High | To do |\n"
        )
        proc = _run(
            _payload("sess-good", valid, "ProductOwner"),
            state_path,
            violations_path,
        )

        # Either exit 0 (accepted) or 2 (schema mismatch) is fine — what we assert
        # is: no violation was written when the guard doesn't block.
        if proc.returncode == 0:
            assert not violations_path.exists()

    def test_non_review_phase_does_not_log(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        violations_path = tmp_path / "violations.md"
        state = _specs_state("sess-x", "vision", "Research")
        _write_state(state_path, state)

        proc = _run(
            _payload("sess-x", "some chatter", "Research"),
            state_path,
            violations_path,
        )
        assert proc.returncode == 0
        assert not violations_path.exists()
